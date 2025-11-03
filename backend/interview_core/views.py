import logging
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import InterviewQuestion, UserAnswer, SavedQuestion
from .serializers import RegisterSerializer, InterviewQuestionSerializer, UserAnswerSerializer, UserSerializer, SavedQuestionSerializer
from .services import InterviewService
from .pagination import StandardResultsSetPagination

logger = logging.getLogger(__name__)

# --------------------
# Auth Views
# --------------------

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = []

# --------------------
# Questions
# --------------------

class InterviewQuestionListView(generics.ListAPIView):
    serializer_class = InterviewQuestionSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return InterviewQuestion.objects.filter(user=self.request.user).order_by('-created_at')



class GenerateQuestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, topic):
        count = int(request.GET.get('count', 4))
        difficulty = request.GET.get('difficulty', 'medium')
        
        try:
            interview_service = InterviewService()
            created_questions = interview_service.create_questions(request.user, topic, count, difficulty)
            
            serializer = InterviewQuestionSerializer(created_questions, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Failed to generate questions for topic {topic}: {str(e)}")
            return Response(
                {"error": "Failed to generate questions. Please try again later."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        topic = request.data.get('topic')
        count = int(request.data.get('count', 4))
        difficulty = request.data.get('difficulty', 'medium')
        
        if not topic:
            return Response({"error": "Topic is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            interview_service = InterviewService()
            created_questions = interview_service.create_questions(request.user, topic, count, difficulty)
            
            # Redirect to interview page
            from django.shortcuts import redirect
            return redirect('interview', topic=topic)
        
        except Exception as e:
            logger.error(f"Failed to generate questions for topic {topic}: {str(e)}")
            return Response(
                {"error": "Failed to generate questions. Please try again later."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# --------------------
# Answer Handling
# --------------------

class UserAnswerCreateView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        audio_file = request.FILES.get('audio_file')
        question_id = request.data.get('question_id')

        if not audio_file or not question_id:
            return Response(
                {"error": "Missing audio file or question ID"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            interview_service = InterviewService()
            answer = interview_service.process_answer(
                request.user, question_id, audio_file
            )
            
            serializer = UserAnswerSerializer(answer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Failed to process answer for question {question_id}: {str(e)}")
            return Response(
                {"error": "Failed to process your answer. Please try again."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

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
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return SavedQuestion.objects.filter(user=self.request.user)
