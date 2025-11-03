from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import models
from .models import InterviewQuestion, UserAnswer, SavedQuestion
from .services import InterviewService
from .serializers import RegisterSerializer
import json

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
    # Optimized user stats with single query
    from django.db.models import Count, Avg
    
    stats = InterviewQuestion.objects.filter(user=request.user).aggregate(
        total_questions=Count('id'),
        answered_questions=Count('id', filter=models.Q(is_answered=True))
    )
    
    total_questions = stats['total_questions']
    answered_questions = stats['answered_questions']
    completion_rate = (answered_questions / total_questions * 100) if total_questions > 0 else 0
    
    # Get average accuracy with single query
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
    }
    
    return render(request, 'interview_core/interview.html', context)

@login_required
@csrf_exempt
def submit_answer_view(request):
    if request.method == 'POST':
        try:
            question_id = request.POST.get('question_id')
            audio_file = request.FILES.get('audio_file')
            
            print(f"DEBUG: question_id={question_id}, audio_file={audio_file}")
            
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
            print(f"ERROR in submit_answer_view: {str(e)}")
            import traceback
            traceback.print_exc()
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
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: Request POST keys: {list(request.POST.keys())}")
    print(f"DEBUG: Request FILES keys: {list(request.FILES.keys())}")
    
    if request.method == 'POST':
        print(f"DEBUG: POST data: {request.POST}")
        print(f"DEBUG: FILES data: {request.FILES}")
        
        resume_file = request.FILES.get('resume')
        count = int(request.POST.get('count', 4))
        difficulty = request.POST.get('difficulty', 'medium')
        
        print(f"DEBUG: resume_file={resume_file}")
        print(f"DEBUG: count={count}")
        print(f"DEBUG: difficulty={difficulty}")
        
        # Store count in session for interview view
        request.session['interview_count'] = count
        
        print(f"DEBUG: Checking if resume_file exists...")
        print(f"DEBUG: About to start resume processing")
        
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
                
                print(f"\n=== STEP 4: RESUME SAVED TO DATABASE ===")
                print(f"DEBUG: Resume saved with ID: {resume.id}")
                
                print(f"\n=== STEP 5: PREPARING KEYWORDS FOR AI MODEL ===")
                # Generate questions based on resume
                interview_service = InterviewService()
                all_questions = []
                
                # Generate questions for each category
                categories = {
                    'Skills': parsed_data['skills'][:3],  # Top 3 skills
                    'Experience': parsed_data['experience'][:2],  # Top 2 experiences
                    'Projects': parsed_data['projects'][:2]  # Top 2 projects
                }
                
                print(f"DEBUG: Categories prepared for AI: {categories}")
                questions_per_category = max(1, count // len([c for c in categories.values() if c]))
                print(f"DEBUG: Questions per category: {questions_per_category}")
                
                print(f"\n=== STEP 6: GENERATING QUESTIONS WITH AI MODEL ===")
                for category, items in categories.items():
                    if items:
                        topic_context = f"{category}: {', '.join(items)}"
                        print(f"DEBUG: Sending to AI model - Topic: {topic_context}")
                        try:
                            questions = interview_service.create_questions(
                                request.user, 
                                topic_context, 
                                questions_per_category,
                                difficulty
                            )
                            all_questions.extend(questions)
                            print(f"DEBUG: AI SUCCESS - Generated {len(questions)} questions for {category}")
                        except Exception as e:
                            print(f"DEBUG: AI FAILED for {category}: {str(e)}")
                            # Create fallback question for this category
                            from .models import InterviewQuestion
                            fallback_question = InterviewQuestion.objects.create(
                                user=request.user,
                                topic="Resume-Based",
                                question=f"Tell me about your experience with {category.lower()}.",
                                answer=f"Describe your background and expertise in {category.lower()}."
                            )
                            all_questions.append(fallback_question)
                            print(f"DEBUG: Created fallback question for {category}")
                
                print(f"\n=== STEP 7: FINALIZING QUESTIONS ===")
                if all_questions:
                    print(f"DEBUG: SUCCESS - Total generated {len(all_questions)} questions")
                    messages.success(request, f'Generated {len(all_questions)} personalized questions based on your resume!')
                else:
                    print("DEBUG: No questions generated, creating fallback")
                    # Create a fallback question if everything fails
                    from .models import InterviewQuestion
                    fallback_question = InterviewQuestion.objects.create(
                        user=request.user,
                        topic="Resume-Based",
                        question="Tell me about your most significant project and the technologies you used.",
                        answer="Describe the project scope, your role, technical challenges, and key achievements."
                    )
                    messages.success(request, 'Generated personalized questions based on your resume!')
                
                print(f"\n=== STEP 8: REDIRECTING TO INTERVIEW ===")
                
                # Delete resume data after questions are generated
                resume.delete()
                print(f"DEBUG: Resume data deleted after question generation")
                
                return redirect('interview', topic='Resume-Based')
                
            except Exception as e:
                print(f"ERROR in upload_resume_view: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Failed to process resume: {str(e)}')
        else:
            messages.error(request, 'Please upload a resume file.')
    
    return redirect('dashboard')



@login_required
def resume_interview_view(request):
    return render(request, 'interview_core/resume_interview.html')

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