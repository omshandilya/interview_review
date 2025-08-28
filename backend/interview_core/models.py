from django.db import models
from django.contrib.auth.models import User

class InterviewQuestion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="questions")
    topic = models.CharField(max_length=100)
    question = models.TextField()
    answer = models.TextField()
    is_answered = models.BooleanField(default=False)
    def __str__(self):
        return self.question[:50]

class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(InterviewQuestion, on_delete=models.CASCADE)
    audio_file = models.FileField(upload_to="answers/")
    user_text = models.TextField(null=True, blank=True)
    accuracy = models.FloatField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    timestamp = models.DateTimeField(auto_now_add=True)  
    def __str__(self):
        return f"{self.user.username} - Q{self.question.id}"
    
class SavedQuestion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(InterviewQuestion, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'question')

    def __str__(self):
        return f"{self.user.username} - {self.question.question[:50]}"