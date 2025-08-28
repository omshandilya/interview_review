# API_KEY = "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"
import os
import json
import re
import whisper
import requests
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.files.storage import default_storage
from rest_framework import serializers
from .models import User, InterviewQuestion, UserAnswer, SavedQuestion
from .serializers import RegisterSerializer, InterviewQuestionSerializer, UserAnswerSerializer, UserSerializer, SavedQuestionSerializer

# --------------------
# Configuration
# --------------------

API_KEY = "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"
WHISPER_MODEL = whisper.load_model("base")
OPENROUTER_API_KEY = API_KEY

# --------------------
# Auth Views
# --------------------

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

# --------------------
# Questions
# --------------------

class InterviewQuestionListView(generics.ListAPIView):
    queryset = InterviewQuestion.objects.all()
    serializer_class = InterviewQuestionSerializer

def call_openrouter(topic):
    prompt = f"""
Generate 4 {topic} interview questions with their sample answers.
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

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "http://localhost",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        raw_content = response.json()['choices'][0]['message']['content']
        match = re.search(r'\[\s*{.*?}\s*\]', raw_content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError as e:
                return f"JSON parsing error: {str(e)}\nExtracted: {match.group()}"
        else:
            return f"Could not find JSON array in response:\n{raw_content}"

    return f"Error: {response.status_code} - {response.text}"

class GenerateQuestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, topic):
        result = call_openrouter(topic)

        if isinstance(result, str):
            return Response({"error": result}, status=500)

        created_questions = []
        for item in result:
            q = InterviewQuestion.objects.create(
                user=request.user,
                topic=topic,
                question=item.get("question", ""),
                answer=item.get("answer", "")
            )
            created_questions.append(q)

        serializer = InterviewQuestionSerializer(created_questions, many=True)
        return Response(serializer.data, status=201)

# --------------------
# Answer Handling
# --------------------

def transcribe_audio(file_path):
    result = WHISPER_MODEL.transcribe(file_path)
    return result['text']

def compare_answers(reference, user_response):
    prompt = f"""
Compare these two answers and return a JSON object having detailed feedback with:
- accuracy (percentage 0–100)
- feedback

Reference Answer: {reference}
User Answer: {user_response}

Respond like:
{{
  "accuracy": 74,
  "feedback": "Good start, but you missed the explanation of Stateful Widgets."
}}
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "http://localhost",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    if response.status_code == 200:
        return json.loads(response.json()['choices'][0]['message']['content'])
    else:
        return {"accuracy": 0, "feedback": "API failed."}

class UserAnswerCreateView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        audio_file = request.FILES.get('audio_file')
        question_id = request.data.get('question_id')

        if not audio_file or not question_id:
            return Response({"error": "Missing file or question ID"}, status=400)

        user = request.user
        question = InterviewQuestion.objects.get(id=question_id, user=user)

        temp_path = default_storage.save(audio_file.name, audio_file)
        full_path = os.path.join(default_storage.location, temp_path)

        user_text = transcribe_audio(full_path)

        comparison = compare_answers(question.answer, user_text)
        accuracy = comparison.get("accuracy", 0)
        feedback = comparison.get("feedback", "No feedback")

        question.is_answered = True
        question.save()  

        answer = UserAnswer.objects.create(
            user=user,
            question=question,
            audio_file=audio_file,
            user_text=user_text,
            accuracy=accuracy,
            feedback=feedback
        )

        serializer = UserAnswerSerializer(answer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

class FullUserReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        questions = InterviewQuestion.objects.filter(user=user)
        answers = UserAnswer.objects.filter(user=user)

        q_serializer = InterviewQuestionSerializer(questions, many=True)
        a_serializer = UserAnswerSerializer(answers, many=True)

        return Response({
            "questions": q_serializer.data,
            "answers": a_serializer.data,
        })



class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# -------------------- Code for Saving questions and displaying them on the profile page --------------------
class SaveQuestionView(generics.CreateAPIView):
    serializer_class = SavedQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        question_id = self.request.data.get('question')
        if not question_id:
            raise serializers.ValidationError({'question': 'This field is required.'})
        serializer.save(user=self.request.user, question_id=question_id)


class ListSavedQuestionsView(generics.ListAPIView):
    serializer_class = SavedQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedQuestion.objects.filter(user=self.request.user)
