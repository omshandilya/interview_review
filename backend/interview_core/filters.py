from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg, Q
from .models import InterviewQuestion, UserAnswer

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        total_questions = InterviewQuestion.objects.filter(user=user).count()
        answered_questions = InterviewQuestion.objects.filter(user=user, is_answered=True).count()
        avg_accuracy = UserAnswer.objects.filter(user=user).aggregate(
            avg_acc=Avg('accuracy')
        )['avg_acc'] or 0
        
        # Topic-wise stats
        topic_stats = InterviewQuestion.objects.filter(user=user).values('topic').annotate(
            total=Count('id'),
            answered=Count('id', filter=Q(is_answered=True))
        )
        
        return Response({
            'total_questions': total_questions,
            'answered_questions': answered_questions,
            'completion_rate': (answered_questions / total_questions * 100) if total_questions > 0 else 0,
            'average_accuracy': round(avg_accuracy, 1),
            'topic_stats': list(topic_stats)
        })