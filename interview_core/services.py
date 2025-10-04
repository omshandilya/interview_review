import os
import json
import re
import whisper
import requests
from django.conf import settings
from django.core.files.storage import default_storage
from .models import InterviewQuestion, UserAnswer


class AIService:
    """Service for handling AI-related operations"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "mistralai/mistral-7b-instruct"
    
    def generate_questions(self, topic, count=4):
        """Generate interview questions for a given topic"""
        prompt = f"""
Generate {count} {topic} interview questions with their sample answers.
Respond ONLY in valid JSON format as a list of objects like this:

[
  {{
    "question": "What is Flutter?",
    "answer": "Flutter is an open-source UI toolkit developed by Google for building mobile, web, and desktop apps from a single codebase."
  }},
  ...
]

Do not include any explanations or markdown (no ```json).
"""
        
        try:
            response = self._make_api_request(prompt)
            return self._parse_json_response(response)
        except Exception as e:
            raise Exception(f"Failed to generate questions: {str(e)}")
    
    def compare_answers(self, reference_answer, user_answer):
        """Compare user answer with reference answer"""
        prompt = f"""
Compare these two answers and return a JSON object having detailed feedback with:
- accuracy (percentage 0–100)
- feedback

Reference Answer: {reference_answer}
User Answer: {user_answer}

Respond like:
{{
  "accuracy": 74,
  "feedback": "Good start, but you missed the explanation of Stateful Widgets."
}}
"""
        
        try:
            response = self._make_api_request(prompt)
            return json.loads(response)
        except Exception as e:
            return {"accuracy": 0, "feedback": f"Analysis failed: {str(e)}"}
    
    def _make_api_request(self, prompt):
        """Make API request to OpenRouter"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
        
        return response.json()['choices'][0]['message']['content']
    
    def _parse_json_response(self, raw_content):
        """Parse JSON from API response"""
        # First try to find a complete JSON array
        array_match = re.search(r'\[\s*{.*?}\s*\]', raw_content, re.DOTALL)
        if array_match:
            try:
                return json.loads(array_match.group())
            except json.JSONDecodeError:
                pass
        
        # If no array found, try to extract individual JSON objects and wrap them in an array
        objects = re.findall(r'{[^{}]*(?:{[^{}]*}[^{}]*)*}', raw_content)
        if objects:
            try:
                parsed_objects = []
                for obj_str in objects:
                    parsed_objects.append(json.loads(obj_str))
                return parsed_objects
            except json.JSONDecodeError as e:
                pass
        
        # If all else fails, try to manually construct the array
        try:
            # Wrap the content in brackets if it's not already an array
            if not raw_content.strip().startswith('['):
                raw_content = '[' + raw_content.strip().rstrip(',') + ']'
            return json.loads(raw_content)
        except json.JSONDecodeError as e:
            raise Exception(f"JSON parsing error: {str(e)}. Raw content: {raw_content}")


class AudioService:
    """Service for handling audio processing"""
    
    def __init__(self):
        self.whisper_model = whisper.load_model("base")
    
    def transcribe_audio(self, audio_file):
        """Transcribe audio file to text"""
        try:
            temp_path = default_storage.save(audio_file.name, audio_file)
            full_path = os.path.join(default_storage.location, temp_path)
            
            result = self.whisper_model.transcribe(full_path)
            
            # Clean up temporary file
            default_storage.delete(temp_path)
            
            return result['text']
        except Exception as e:
            raise Exception(f"Audio transcription failed: {str(e)}")


class InterviewService:
    """Service for handling interview-related business logic"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.audio_service = AudioService()
    
    def create_questions(self, user, topic, count=4):
        """Create interview questions for a user"""
        questions_data = self.ai_service.generate_questions(topic, count)
        
        created_questions = []
        for item in questions_data:
            question = InterviewQuestion.objects.create(
                user=user,
                topic=topic,
                question=item.get("question", ""),
                answer=item.get("answer", "")
            )
            created_questions.append(question)
        
        return created_questions
    
    def process_answer(self, user, question_id, audio_file):
        """Process user's audio answer"""
        try:
            question = InterviewQuestion.objects.get(id=question_id, user=user)
        except InterviewQuestion.DoesNotExist:
            raise Exception("Question not found")
        
        # Transcribe audio
        user_text = self.audio_service.transcribe_audio(audio_file)
        
        # Compare with reference answer
        comparison = self.ai_service.compare_answers(question.answer, user_text)
        
        # Mark question as answered
        question.is_answered = True
        question.save()
        
        # Create answer record
        answer = UserAnswer.objects.create(
            user=user,
            question=question,
            audio_file=audio_file,
            user_text=user_text,
            accuracy=comparison.get("accuracy", 0),
            feedback=comparison.get("feedback", "No feedback")
        )
        
        return answer