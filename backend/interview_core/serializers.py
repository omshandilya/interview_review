from rest_framework import serializers, generics, permissions
from django.contrib.auth.models import User
from .models import InterviewQuestion, UserAnswer, SavedQuestion

# -------------------- Registration Serializer --------------------
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

# -------------------- Question Serializer --------------------
class InterviewQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewQuestion
        fields = ['id', 'topic', 'question', 'answer']

# -------------------- Answer Serializer --------------------
class UserAnswerSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    question = InterviewQuestionSerializer(read_only=True)

    class Meta:
        model = UserAnswer
        fields = ['id', 'user', 'question', 'user_text', 'accuracy', 'feedback', 
                 'strengths', 'improvements', 'missing_points', 'clarity_score', 
                 'completeness_score', 'technical_accuracy_score', 'created_at']

# -------------------- Profile Update Serializer --------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            instance.set_password(validated_data.pop('password'))
        return super().update(instance, validated_data)

# -------------------- Saved Question Serializer --------------------
class SavedQuestionSerializer(serializers.ModelSerializer):
    question = InterviewQuestionSerializer(read_only=True)
    answer = serializers.SerializerMethodField()

    class Meta:
        model = SavedQuestion
        fields = ['id', 'question', 'saved_at', 'answer']

    def get_answer(self, obj):
        user = obj.user
        question = obj.question
        answer = UserAnswer.objects.filter(user=user, question=question).order_by('-created_at').first()
        if answer:
            return {
                "id": answer.id,
                "audio_file": answer.audio_file.url if answer.audio_file else None,
                "feedback": answer.feedback,
                "submitted_at": answer.created_at,
            }
        return None

class ListSavedQuestionsView(generics.ListAPIView):
    serializer_class = SavedQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedQuestion.objects.filter(user=self.request.user)


