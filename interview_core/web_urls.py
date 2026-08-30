from django.urls import path
from .template_views import (
    login_view, register_view, logout_view, dashboard_view,
    generate_questions_view, interview_view, submit_answer_view,
    save_question_view, saved_questions_view, profile_view, upload_resume_view,
    resume_interview_view
)

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('generate-questions/', generate_questions_view, name='generate_questions'),
    path('interview/<str:topic>/', interview_view, name='interview'),
    path('submit-answer/', submit_answer_view, name='submit_answer'),
    path('save-question/<int:question_id>/', save_question_view, name='save_question'),
    path('saved-questions/', saved_questions_view, name='saved_questions'),
    path('profile/', profile_view, name='profile'),
    path('resume-interview/', resume_interview_view, name='resume_interview'),
    path('upload-resume/', upload_resume_view, name='upload_resume'),
]