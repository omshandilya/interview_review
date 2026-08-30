from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

class InterviewQuestion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="questions")
    topic = models.CharField(max_length=100, db_index=True)
    question = models.TextField()
    answer = models.TextField()
    is_answered = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'topic']),
            models.Index(fields=['user', 'is_answered']),
        ]
    
    def __str__(self):
        return f"{self.topic}: {self.question[:50]}"

class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(InterviewQuestion, on_delete=models.CASCADE, related_name="user_answers")
    user_text = models.TextField()
    accuracy = models.FloatField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    
    # Enhanced feedback fields
    strengths = models.TextField(null=True, blank=True)
    improvements = models.TextField(null=True, blank=True)
    missing_points = models.TextField(null=True, blank=True)
    clarity_score = models.FloatField(null=True, blank=True)
    completeness_score = models.FloatField(null=True, blank=True)
    technical_accuracy_score = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'question']  # One answer per user per question
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['question', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.question.topic} - Q{self.question.id}"
    
class SavedQuestion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_questions")
    question = models.ForeignKey(InterviewQuestion, on_delete=models.CASCADE, related_name="saved_by")
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'question')
        ordering = ['-saved_at']
        indexes = [
            models.Index(fields=['user', 'saved_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.question.question[:50]}"

class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resumes")
    extracted_text = models.TextField(blank=True)
    skills = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    projects = models.JSONField(default=list, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.user.username} - Resume ({self.uploaded_at.date()})"