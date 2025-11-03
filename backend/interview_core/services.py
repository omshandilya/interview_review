import os
import json
import re
import requests
from django.conf import settings
from django.core.files.storage import default_storage
from .models import InterviewQuestion, UserAnswer

try:
    from transformers import pipeline
    import librosa
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class AIService:
    """Service for handling AI-related operations"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "openai/gpt-3.5-turbo"
    
    def generate_questions(self, topic, count=4, difficulty="medium"):
        """Generate interview questions for a given topic with specified difficulty"""
        
        difficulty_descriptions = {
            "easy": "basic concepts, simple definitions, and fundamental knowledge",
            "medium": "practical applications, problem-solving, and intermediate concepts", 
            "hard": "advanced concepts, complex scenarios, system design, and expert-level knowledge"
        }
        
        difficulty_desc = difficulty_descriptions.get(difficulty, difficulty_descriptions["medium"])
        
        prompt = f"""
You are an expert technical interviewer who generates precise, structured interview questions.

🚨 CRITICAL REQUIREMENT: Generate EXACTLY {count} questions - NO MORE, NO LESS! 🚨

Your task:
- Generate **exactly {count}** interview questions about **{topic}**.
- The difficulty level is **{difficulty.upper()}** — described as: {difficulty_desc}.
- IT IS VERY VERY IMPORTANT to generate only {count} questions.
- Do not add any explanations, introductions, or markdown formatting.
- Each question must be conceptually aligned with the difficulty level.
- Each answer must be concise, technically correct, and appropriate to the difficulty.
- Output MUST be valid **JSON** only — no text outside the JSON.

Required output format:
[
  {{
    "question": "string",
    "answer": "string"
  }},
  ...
]

Validation rules:
- Generate EXACTLY {count} objects in the JSON array - THIS IS MANDATORY!
- Each object must have both "question" and "answer" fields.
- Questions should be unique and non-repetitive.
- The topic '{topic}' must clearly appear in all questions.
- The response MUST parse as valid JSON — no extra text, markdown, or commentary.
- REMEMBER: Only {count} questions, not more!
"""
        
        print(f"DEBUG AIService: Requesting {count} questions for '{topic}'")
        
        try:
            response = self._make_api_request(prompt)
            questions = self._parse_json_response(response)
            print(f"DEBUG AIService: AI returned {len(questions)} questions, slicing to {count}")
            return questions[:count]  # Force exact count
        except Exception as e:
            raise Exception(f"Failed to generate questions: {str(e)}")
    
    def compare_answers(self, reference_answer, user_answer, question_text=""):
        """Compare user answer with reference answer and provide detailed feedback"""
        prompt = f"""
You are an expert technical interviewer. Analyze this interview answer and provide specific, detailed feedback.

Question: {question_text}
Expected Answer: {reference_answer}
Candidate's Answer: {user_answer}

Analyze the candidate's response and provide feedback in JSON format. Be specific and avoid generic responses.

Return ONLY valid JSON in this format:
{{
  "accuracy": [score 0-100],
  "feedback": "[specific overall assessment of the answer]",
  "strengths": "[specific strengths found in this answer]",
  "improvements": "[specific areas this answer could improve]",
  "missing_points": "[specific important points not covered]",
  "clarity_score": [score 0-100],
  "completeness_score": [score 0-100],
  "technical_accuracy_score": [score 0-100]
}}

IMPORTANT: 
- Be specific to the actual content of the user's answer
- Avoid generic phrases like "good examples" unless there actually are examples
- Focus on the technical accuracy and completeness relative to the expected answer
- Provide actionable, specific feedback
"""
        
        try:
            response = self._make_api_request(prompt)
            result = json.loads(response)
            
            # Ensure all required fields exist with defaults
            return {
                "accuracy": result.get("accuracy", 0),
                "feedback": result.get("feedback", "No feedback available"),
                "strengths": result.get("strengths", "None identified"),
                "improvements": result.get("improvements", "None suggested"),
                "missing_points": result.get("missing_points", "None identified"),
                "clarity_score": result.get("clarity_score", 0),
                "completeness_score": result.get("completeness_score", 0),
                "technical_accuracy_score": result.get("technical_accuracy_score", 0)
            }
        except Exception as e:
            return {
                "accuracy": 0,
                "feedback": f"Analysis failed: {str(e)}",
                "strengths": "Analysis unavailable",
                "improvements": "Analysis unavailable",
                "missing_points": "Analysis unavailable",
                "clarity_score": 0,
                "completeness_score": 0,
                "technical_accuracy_score": 0
            }
    
    def _make_api_request(self, prompt):
        """Make API request to OpenRouter"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        
        response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
        
        return response.json()['choices'][0]['message']['content']
    
    def _parse_json_response(self, raw_content):
        """Parse JSON from API response with better error handling"""
        # Clean the response
        content = raw_content.strip()
        
        # Remove common prefixes/suffixes that models add
        if content.startswith('[<s>]') or content.startswith('<s>'):
            content = content.replace('[<s>]', '').replace('<s>', '').strip()
        if content.endswith('</s>'):
            content = content.replace('</s>', '').strip()
        
        # Try direct JSON parsing first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON array pattern
        array_match = re.search(r'\[\s*{.*?}\s*\]', content, re.DOTALL)
        if array_match:
            try:
                return json.loads(array_match.group())
            except json.JSONDecodeError:
                pass
        
        # Extract individual JSON objects
        objects = re.findall(r'{[^{}]*(?:{[^{}]*}[^{}]*)*}', content)
        if objects:
            try:
                parsed_objects = []
                for obj_str in objects:
                    parsed_objects.append(json.loads(obj_str))
                return parsed_objects
            except json.JSONDecodeError:
                pass
        
        # Last resort: return mock data to prevent complete failure
        return [{
            "question": "What is your experience with this technology?",
            "answer": "Please describe your hands-on experience and key projects."
        }]


class AudioService:
    """Service for handling audio processing"""
    
    def __init__(self):
        self.transcriber = None
        if TRANSFORMERS_AVAILABLE:
            try:
                self.transcriber = pipeline(
                    "automatic-speech-recognition",
                    model="openai/whisper-tiny",
                    device=-1  # Use CPU
                )
            except Exception as e:
                print(f"Failed to load Whisper model: {e}")
    
    def transcribe_audio(self, audio_file):
        """Transcribe audio file to text using Hugging Face Whisper"""
        if not self.transcriber:
            return "Audio transcription unavailable. Please type your answer."
        
        try:
            import tempfile
            import numpy as np
            
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                for chunk in audio_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            # Load audio with librosa
            audio_data, sample_rate = librosa.load(temp_path, sr=16000)
            
            # Transcribe using Hugging Face pipeline
            result = self.transcriber(audio_data)
            
            # Clean up temp file
            os.unlink(temp_path)
            
            return result['text']
            
        except Exception as e:
            return f"Transcription failed: Please type your answer."


class InterviewService:
    """Service for handling interview-related business logic"""
    
    def __init__(self):
        self.ai_service = AIService()
        try:
            self.audio_service = AudioService()
        except Exception as e:
            print(f"AudioService initialization failed: {e}")
            self.audio_service = None
    
    def create_questions(self, user, topic, count=4, difficulty="medium"):
        """Create interview questions for a user with specified count and difficulty"""
        questions_data = self.ai_service.generate_questions(topic, count, difficulty)
        
        print(f"DEBUG InterviewService: Creating {len(questions_data)} questions in database")
        
        created_questions = []
        for item in questions_data:
            question = InterviewQuestion.objects.create(
                user=user,
                topic=topic,
                question=item.get("question", ""),
                answer=item.get("answer", "")
            )
            created_questions.append(question)
        
        print(f"DEBUG InterviewService: Created {len(created_questions)} questions")
        return created_questions
    
    def process_answer(self, user, question_id, audio_file):
        """Process user's audio answer"""
        try:
            question = InterviewQuestion.objects.get(id=question_id, user=user)
        except InterviewQuestion.DoesNotExist:
            raise Exception("Question not found")
        
        # Transcribe audio (temporary processing)
        user_text = self.audio_service.transcribe_audio(audio_file)
        
        # Compare with reference answer
        comparison = self.ai_service.compare_answers(question.answer, user_text, question.question)
        
        # Mark question as answered
        question.is_answered = True
        question.save()
        
        # Create or update answer record with enhanced feedback
        answer, created = UserAnswer.objects.get_or_create(
            user=user,
            question=question,
            defaults={
                'user_text': user_text,
                'accuracy': comparison.get("accuracy", 0),
                'feedback': comparison.get("feedback", "No feedback"),
                'strengths': comparison.get("strengths", ""),
                'improvements': comparison.get("improvements", ""),
                'missing_points': comparison.get("missing_points", ""),
                'clarity_score': comparison.get("clarity_score", 0),
                'completeness_score': comparison.get("completeness_score", 0),
                'technical_accuracy_score': comparison.get("technical_accuracy_score", 0)
            }
        )
        
        # Update existing answer if not created
        if not created:
            answer.user_text = user_text
            answer.accuracy = comparison.get("accuracy", 0)
            answer.feedback = comparison.get("feedback", "No feedback")
            answer.strengths = comparison.get("strengths", "")
            answer.improvements = comparison.get("improvements", "")
            answer.missing_points = comparison.get("missing_points", "")
            answer.clarity_score = comparison.get("clarity_score", 0)
            answer.completeness_score = comparison.get("completeness_score", 0)
            answer.technical_accuracy_score = comparison.get("technical_accuracy_score", 0)
            answer.save()
        return answer