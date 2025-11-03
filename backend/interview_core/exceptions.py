class InterviewServiceError(Exception):
    """Base exception for interview service errors"""
    pass

class AIServiceError(InterviewServiceError):
    """Exception for AI service related errors"""
    pass

class AudioProcessingError(InterviewServiceError):
    """Exception for audio processing errors"""
    pass

class QuestionNotFoundError(InterviewServiceError):
    """Exception when question is not found"""
    pass