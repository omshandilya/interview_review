from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

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

def custom_exception_handler(exc, context):
    """Custom exception handler to prevent sensitive data leakage"""
    response = exception_handler(exc, context)
    
    if response is not None:
        # Sanitize error messages in production
        from django.conf import settings
        if not settings.DEBUG:
            response.data = {
                'error': 'An error occurred. Please try again later.',
                'status_code': response.status_code
            }
        return response
    
    # Handle unexpected errors
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return Response(
        {'error': 'An unexpected error occurred. Please contact support.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )