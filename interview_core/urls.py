from django.urls import path
from .views import RegisterView, InterviewQuestionListView, SaveQuestionView, ListSavedQuestionsView, UserAnswerCreateView, GenerateQuestionsView, FullUserReportView, UserProfileView
from .filters import DashboardStatsView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.http import JsonResponse


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('questions/', InterviewQuestionListView.as_view(), name='questions'),
    path('submit-answer/', UserAnswerCreateView.as_view(), name='submit-answer'),
    path('generate-questions/<str:topic>/', GenerateQuestionsView.as_view(), name='generate-questions'),
    path('generate-questions/', GenerateQuestionsView.as_view(), name='generate_questions'),
    path('report/', FullUserReportView.as_view(), name='full-user-report'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("test-token/", lambda r: JsonResponse({"message": "token route works"})),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('save-question/', SaveQuestionView.as_view(), name='save-question'),   
    path('saved-questions/', ListSavedQuestionsView.as_view(), name='saved-questions'),
    path('dashboard-stats/', DashboardStatsView.as_view(), name='dashboard-stats'),

]
