from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.db import models
from .models import InterviewQuestion, RoleInterviewSession, UserAnswer, SavedQuestion
from .role_catalog import (
    EXPERIENCE_LEVELS,
    FOCUS_AREAS,
    ROLE_OPTIONS,
    label_for,
    normalize_custom_role,
)
from .services import InterviewService
from .serializers import RegisterSerializer
import json
import logging
from hashlib import sha256

logger = logging.getLogger(__name__)


@login_required
@require_POST
def synthesize_speech_view(request):
    """Return Google Neural2 speech for a short interview prompt.

    The endpoint deliberately keeps Google credentials server-side. A 503 is
    returned for configuration/provider errors so the client can immediately
    fall back to the browser's native speech synthesis.
    """
    if not settings.GOOGLE_TTS_ENABLED:
        return JsonResponse({'error': 'Cloud text-to-speech is disabled.'}, status=503)

    try:
        payload = json.loads(request.body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Request body must be valid JSON.'}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({'error': 'Request body must be a JSON object.'}, status=400)

    text = payload.get('text', '')
    if not isinstance(text, str) or not text.strip():
        return JsonResponse({'error': 'Text is required.'}, status=400)
    if len(text) > 5_000:
        return JsonResponse({'error': 'Text must be 5,000 characters or fewer.'}, status=400)

    text = text.strip()
    cache_hash = sha256(
        f'{settings.GOOGLE_TTS_VOICE}:{settings.GOOGLE_TTS_LANGUAGE_CODE}:{text}'.encode()
    ).hexdigest()
    cache_key = f'neural2_audio:{cache_hash}'
    audio_content = cache.get(cache_key)

    if audio_content is None:
        try:
            from google.cloud import texttospeech
            from google.oauth2 import service_account

            credentials = None
            if settings.GOOGLE_APPLICATION_CREDENTIALS_JSON:
                credentials = service_account.Credentials.from_service_account_info(
                    json.loads(settings.GOOGLE_APPLICATION_CREDENTIALS_JSON)
                )

            client = texttospeech.TextToSpeechClient(credentials=credentials)
            response = client.synthesize_speech(
                input=texttospeech.SynthesisInput(text=text),
                voice=texttospeech.VoiceSelectionParams(
                    language_code=settings.GOOGLE_TTS_LANGUAGE_CODE,
                    name=settings.GOOGLE_TTS_VOICE,
                ),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                ),
            )
            audio_content = response.audio_content
            cache.set(cache_key, audio_content, timeout=60 * 60)
        except Exception:
            logger.exception('Google Cloud Text-to-Speech synthesis failed')
            return JsonResponse({'error': 'Cloud text-to-speech is unavailable.'}, status=503)

    response = HttpResponse(audio_content, content_type='audio/mpeg')
    response['Cache-Control'] = 'private, max-age=3600'
    return response

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials')
    
    return render(request, 'interview_core/login.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        serializer = RegisterSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.save()
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    return render(request, 'interview_core/register.html')

@login_required
def dashboard_view(request):
    from django.db.models import Count, Avg
    from django.core.cache import cache
    
    cache_key = f'dashboard_template_{request.user.id}'
    context = cache.get(cache_key)
    
    if not context:
        stats = InterviewQuestion.objects.filter(user=request.user).aggregate(
            total_questions=Count('id'),
            answered_questions=Count('id', filter=models.Q(is_answered=True))
        )
        
        total_questions = stats['total_questions']
        answered_questions = stats['answered_questions']
        completion_rate = (answered_questions / total_questions * 100) if total_questions > 0 else 0
        
        avg_accuracy_result = UserAnswer.objects.filter(user=request.user).aggregate(
            avg_accuracy=Avg('accuracy')
        )
        avg_accuracy = avg_accuracy_result['avg_accuracy'] or 0
        
        context = {
            'total_questions': total_questions,
            'answered_questions': answered_questions,
            'completion_rate': round(completion_rate, 1),
            'average_accuracy': round(avg_accuracy, 1),
        }
        # Cache for 5 minutes
        cache.set(cache_key, context, 300)
    
    return render(request, 'interview_core/dashboard.html', context)

@login_required
def generate_questions_view(request):
    if request.method == 'POST':
        topics_str = request.POST.get('topics')
        count = int(request.POST.get('count', 4))
        difficulty = request.POST.get('difficulty', 'medium')
        
        # Store count in session for interview view
        request.session['interview_count'] = count
        
        if topics_str:
            topics = [t.strip() for t in topics_str.split(',') if t.strip()]
            if topics:
                try:
                    interview_service = InterviewService()
                    all_questions = []
                    
                    # Generate questions for each topic
                    questions_per_topic = max(1, count // len(topics))
                    for topic in topics:
                        questions = interview_service.create_questions(request.user, topic, questions_per_topic, difficulty)
                        all_questions.extend(questions)
                    
                    # If we need more questions to reach the count
                    remaining = count - len(all_questions)
                    if remaining > 0:
                        extra_questions = interview_service.create_questions(request.user, topics[0], remaining, difficulty)
                        all_questions.extend(extra_questions)
                    
                    topics_display = ', '.join(topics)
                    messages.success(request, f'Generated {len(all_questions)} questions for {topics_display}')
                    return redirect('interview', topic='Mixed')
                except Exception as e:
                    messages.error(request, 'Failed to generate questions. Please try again.')
    
    return redirect('dashboard')

@login_required
def interview_view(request, topic):
    # Get requested count from session or default to 4
    requested_count = request.session.get('interview_count', 4)
    
    # Optimized queries with select_related for foreign keys
    if topic == 'Mixed':
        questions = InterviewQuestion.objects.select_related('user').filter(
            user=request.user
        ).order_by('-created_at')[:requested_count]
    elif topic == 'Resume-Based':
        questions = InterviewQuestion.objects.select_related('user').filter(
            user=request.user
        ).order_by('-created_at')[:requested_count]
    else:
        questions = InterviewQuestion.objects.select_related('user').filter(
            user=request.user, topic=topic
        ).order_by('id')[:requested_count]
    
    if not questions:
        messages.error(request, f'No questions found for topic: {topic}')
        return redirect('dashboard')
    
    # Get current question index
    current_index = int(request.GET.get('q', 0))
    
    if current_index >= len(questions):
        messages.success(request, f'Interview completed!')
        return redirect('dashboard')
    
    current_question = questions[current_index]
    
    context = {
        'topic': topic,
        'current_question': current_question,
        'current_index': current_index,
        'total_questions': len(questions),
        'next_index': current_index + 1,
        'next_url': f"{reverse('interview', args=[topic])}?q={current_index + 1}",
    }
    
    return render(request, 'interview_core/interview.html', context)

@login_required
@csrf_exempt
def submit_answer_view(request):
    if request.method == 'POST':
        try:
            question_id = request.POST.get('question_id')
            audio_file = request.FILES.get('audio_file')
            
            logger.debug("submit_answer: question_id=%s, audio_file=%s", question_id, audio_file)
            
            if not question_id or not audio_file:
                return JsonResponse({'error': 'Missing data'}, status=400)
            
            interview_service = InterviewService()
            answer = interview_service.process_answer(request.user, question_id, audio_file)
            
            return JsonResponse({
                'accuracy': answer.accuracy,
                'feedback': answer.feedback,
                'strengths': answer.strengths,
                'improvements': answer.improvements,
                'missing_points': answer.missing_points,
                'clarity_score': answer.clarity_score,
                'completeness_score': answer.completeness_score,
                'technical_accuracy_score': answer.technical_accuracy_score,
                'success': True
            })
            
        except Exception as e:
            logger.exception("Error in submit_answer_view")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def save_question_view(request, question_id):
    question = get_object_or_404(InterviewQuestion, id=question_id, user=request.user)
    
    saved_question, created = SavedQuestion.objects.get_or_create(
        user=request.user,
        question=question
    )
    
    if created:
        messages.success(request, 'Question saved successfully!')
    else:
        messages.info(request, 'Question already saved.')
    
    if question.role_session_id:
        return redirect('role_interview_session', session_id=question.role_session_id)
    return redirect('interview', topic=question.topic)

@login_required
def saved_questions_view(request):
    # Optimized query with prefetch_related to avoid N+1 queries
    from django.db.models import Prefetch
    
    saved_questions = SavedQuestion.objects.select_related('question').prefetch_related(
        Prefetch(
            'question__user_answers',
            queryset=UserAnswer.objects.filter(user=request.user),
            to_attr='user_answer_list'
        )
    ).filter(user=request.user).order_by('-saved_at')
    
    # Set user_answer attribute for template compatibility
    for saved in saved_questions:
        saved.user_answer = saved.question.user_answer_list[0] if saved.question.user_answer_list else None
    
    return render(request, 'interview_core/saved_questions.html', {'saved_questions': saved_questions})

@login_required
def upload_resume_view(request):
    logger.debug("upload_resume: method=%s, POST keys=%s, FILES keys=%s", request.method, list(request.POST.keys()), list(request.FILES.keys()))
    
    if request.method == 'POST':
        
        resume_file = request.FILES.get('resume')
        count = int(request.POST.get('count', 4))
        difficulty = request.POST.get('difficulty', 'medium')
        
        logger.debug("upload_resume: file=%s, count=%d, difficulty=%s", resume_file, count, difficulty)
        
        # Store count in session for interview view
        request.session['interview_count'] = count
        
        logger.debug("Starting resume processing")
        
        if resume_file:
            try:
                from .resume_parser import ResumeParser
                from .models import Resume
                
                # Parse resume (no file saving)
                parser = ResumeParser()
                parsed_data = parser.process_resume(resume_file)
                
                # Save only extracted data to database
                resume = Resume.objects.create(
                    user=request.user,
                    extracted_text=parsed_data['extracted_text'],
                    skills=parsed_data['skills'],
                    experience=parsed_data['experience'],
                    projects=parsed_data['projects']
                )
                # File is automatically deleted after processing
                
                logger.debug("Resume saved with ID: %d", resume.id)
                
                logger.debug("Preparing keywords for AI model")
                # Generate questions based on resume
                interview_service = InterviewService()
                all_questions = []
                
                # Generate questions for each category
                categories = {
                    'Skills': parsed_data['skills'][:3],  # Top 3 skills
                    'Experience': parsed_data['experience'][:2],  # Top 2 experiences
                    'Projects': parsed_data['projects'][:2]  # Top 2 projects
                }
                
                logger.debug("Categories prepared: %s", categories)
                questions_per_category = max(1, count // len([c for c in categories.values() if c]))
                logger.debug("Questions per category: %d", questions_per_category)
                
                logger.debug("Generating questions with AI model")
                for category, items in categories.items():
                    if items:
                        topic_context = f"{category}: {', '.join(items)}"
                        logger.debug("Sending to AI: topic=%s", topic_context)
                        try:
                            questions = interview_service.create_questions(
                                request.user, 
                                topic_context, 
                                questions_per_category,
                                difficulty
                            )
                            all_questions.extend(questions)
                            logger.info("Generated %d questions for %s", len(questions), category)
                        except Exception as e:
                            logger.warning("AI failed for %s: %s", category, str(e))
                            # Create fallback question for this category
                            from .models import InterviewQuestion
                            fallback_question = InterviewQuestion.objects.create(
                                user=request.user,
                                topic="Resume-Based",
                                question=f"Tell me about your experience with {category.lower()}.",
                                answer=f"Describe your background and expertise in {category.lower()}."
                            )
                            all_questions.append(fallback_question)
                            logger.debug("Created fallback question for %s", category)
                
                logger.debug("Finalizing questions")
                if all_questions:
                    logger.info("Generated total %d questions from resume", len(all_questions))
                    messages.success(request, f'Generated {len(all_questions)} personalized questions based on your resume!')
                else:
                    logger.warning("No questions generated, creating fallback")
                    # Create a fallback question if everything fails
                    from .models import InterviewQuestion
                    fallback_question = InterviewQuestion.objects.create(
                        user=request.user,
                        topic="Resume-Based",
                        question="Tell me about your most significant project and the technologies you used.",
                        answer="Describe the project scope, your role, technical challenges, and key achievements."
                    )
                    messages.success(request, 'Generated personalized questions based on your resume!')
                
                logger.debug("Redirecting to interview")
                
                # Delete resume data after questions are generated
                resume.delete()
                logger.debug("Resume data deleted after question generation")
                
                return redirect('interview', topic='Resume-Based')
                
            except Exception as e:
                logger.exception("Error in upload_resume_view")
                messages.error(request, f'Failed to process resume: {str(e)}')
        else:
            messages.error(request, 'Please upload a resume file.')
    
    return redirect('dashboard')



@login_required
def resume_interview_view(request):
    return render(request, 'interview_core/resume_interview.html')


@login_required
def role_interview_view(request):
    """Display the configuration form for a role-based interview."""
    return render(request, 'interview_core/role_interview.html', {
        'role_options': ROLE_OPTIONS,
        'experience_levels': EXPERIENCE_LEVELS,
        'focus_areas': FOCUS_AREAS,
    })


@login_required
@require_POST
def generate_role_interview_view(request):
    """Validate a role interview request, then generate an isolated question set."""
    role_slug = request.POST.get('role', '').strip()
    custom_role = request.POST.get('custom_role', '')
    role = label_for(ROLE_OPTIONS, role_slug)

    if role_slug == 'custom':
        role, role_slug = normalize_custom_role(custom_role)
    if not role:
        messages.error(request, 'Select a role or enter a role between 2 and 100 characters.')
        return redirect('role_interview')

    experience_level = label_for(EXPERIENCE_LEVELS, request.POST.get('experience_level', ''))
    focus_area = request.POST.get('focus_area', 'mixed')
    difficulty = request.POST.get('difficulty', 'medium')
    if not experience_level:
        messages.error(request, 'Select an experience level.')
        return redirect('role_interview')
    if not label_for(FOCUS_AREAS, focus_area):
        messages.error(request, 'Select a valid interview focus.')
        return redirect('role_interview')
    if difficulty not in {'easy', 'medium', 'hard'}:
        messages.error(request, 'Select a valid difficulty level.')
        return redirect('role_interview')

    try:
        question_count = int(request.POST.get('count', 4))
    except (TypeError, ValueError):
        question_count = 0
    if not 1 <= question_count <= 10:
        messages.error(request, 'Choose between 1 and 10 questions.')
        return redirect('role_interview')

    job_description = request.POST.get('job_description', '').strip()
    if len(job_description) > 12_000:
        messages.error(request, 'Keep the job description to 12,000 characters or fewer.')
        return redirect('role_interview')

    role_session = RoleInterviewSession.objects.create(
        user=request.user,
        role=role,
        role_slug=role_slug,
        experience_level=experience_level,
        focus_area=focus_area,
        job_description=job_description,
        difficulty=difficulty,
        question_count=question_count,
    )
    try:
        questions = InterviewService().create_role_questions(request.user, role_session)
    except Exception:
        role_session.delete()
        logger.exception('Failed to generate role interview for %s', role)
        messages.error(request, 'Unable to generate the role interview. Please try again.')
        return redirect('role_interview')

    if not questions:
        role_session.delete()
        messages.error(request, 'No interview questions were generated. Please try again.')
        return redirect('role_interview')

    cache.delete(f'dashboard_template_{request.user.id}')
    messages.success(request, f'Generated {len(questions)} questions for the {role} role.')
    return redirect('role_interview_session', session_id=role_session.id)


@login_required
def role_interview_session_view(request, session_id):
    """Run one role session without mixing it with prior attempts."""
    role_session = get_object_or_404(RoleInterviewSession, id=session_id, user=request.user)
    questions = list(role_session.questions.order_by('id'))
    if not questions:
        messages.error(request, 'No questions were found for this role interview.')
        return redirect('dashboard')

    try:
        current_index = int(request.GET.get('q', 0))
    except (TypeError, ValueError):
        current_index = 0
    current_index = max(current_index, 0)
    if current_index >= len(questions):
        messages.success(request, 'Role interview completed!')
        return redirect('dashboard')

    return render(request, 'interview_core/interview.html', {
        'topic': role_session.role,
        'role_session': role_session,
        'current_question': questions[current_index],
        'current_index': current_index,
        'total_questions': len(questions),
        'next_index': current_index + 1,
        'next_url': f"{reverse('role_interview_session', args=[role_session.id])}?q={current_index + 1}",
    })

@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)
        
        new_password = request.POST.get('password')
        if new_password:
            user.set_password(new_password)
        
        user.save()
        messages.success(request, 'Profile updated successfully!')
        
        if new_password:
            # Re-authenticate user after password change
            user = authenticate(username=user.username, password=new_password)
            login(request, user)
    
    return render(request, 'interview_core/profile.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('login')
