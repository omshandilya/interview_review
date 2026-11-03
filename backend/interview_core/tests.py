from unittest.mock import Mock, patch
import os

from django.test import SimpleTestCase
from django.core.cache import cache

from .services import AIService, GroqQuestionService, AudioService, TextToSpeechService
from .resume_parser import ResumeParser
from .exceptions import AudioProcessingError


class AIServiceTests(SimpleTestCase):
    def setUp(self):
        # Bypass environment-key validation; API calls are mocked in these tests.
        self.service = object.__new__(AIService)
        self.service.api_key = 'test-key'
        self.service.base_url = 'https://example.test/chat/completions'
        self.service.model = 'test-model'

    @staticmethod
    def response(payload, status_code=200):
        response = Mock(status_code=status_code)
        response.json.return_value = payload
        return response

    @patch('interview_core.services.requests.post')
    def test_retries_an_empty_completion_then_returns_content(self, post):
        empty = self.response({
            'choices': [{'message': {'content': None}, 'finish_reason': 'error'}],
        })
        complete = self.response({
            'choices': [{'message': {'content': '[{"question": "Q", "answer": "A"}]'}}],
        })
        post.side_effect = [empty, complete]

        content = self.service._make_api_request('Generate one question')

        self.assertEqual(content, '[{"question": "Q", "answer": "A"}]')
        self.assertEqual(post.call_count, 2)

    @patch('interview_core.services.requests.post')
    def test_reports_a_provider_error_instead_of_parsing_null_content(self, post):
        post.return_value = self.response({
            'error': {'message': 'No available providers'},
            'choices': [{'message': {'content': None}, 'finish_reason': 'error'}],
        })

        with self.assertRaisesMessage(Exception, 'No available providers'):
            self.service._make_api_request('Generate one question')


class GroqQuestionServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = object.__new__(GroqQuestionService)
        self.service.api_key = 'test-groq-key'
        self.service.base_url = 'https://api.groq.com/openai/v1/chat/completions'
        self.service.model = 'openai/gpt-oss-20b'

    @patch('interview_core.services.requests.post')
    def test_question_generation_uses_the_groq_chat_endpoint(self, post):
        response = Mock(status_code=200)
        response.json.return_value = {
            'choices': [{'message': {'content': '[{"question": "Q", "answer": "A"}]'}}],
        }
        post.return_value = response

        content = self.service._make_api_request('Generate one question')

        self.assertEqual(content, '[{"question": "Q", "answer": "A"}]')
        _, kwargs = post.call_args
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-groq-key')
        self.assertEqual(kwargs['json']['model'], 'openai/gpt-oss-20b')
        self.assertEqual(kwargs['json']['max_completion_tokens'], 2000)


class AudioServiceTests(SimpleTestCase):
    def test_init_raises_value_error_when_key_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                AudioService()
            self.assertIn("GROQ_API_KEY", str(ctx.exception))

    @patch('interview_core.services.requests.post')
    def test_transcribe_audio_raises_audio_processing_error_on_api_error(self, post):
        service = object.__new__(AudioService)
        service.api_key = 'fake-key'
        service.base_url = 'https://api.groq.com/openai/v1/audio/transcriptions'
        service.model = 'whisper-large-v3-turbo'

        mock_file = Mock()
        mock_file.name = 'answer.wav'
        mock_file.read.return_value = b'audio-bytes'
        mock_file.content_type = 'audio/wav'

        post.return_value = Mock(status_code=500, text='Server Error')

        with self.assertRaises(AudioProcessingError):
            service.transcribe_audio(mock_file)

    @patch('interview_core.services.requests.post')
    def test_transcribe_audio_returns_transcribed_text(self, post):
        service = object.__new__(AudioService)
        service.api_key = 'fake-key'
        service.base_url = 'https://api.groq.com/openai/v1/audio/transcriptions'
        service.model = 'whisper-large-v3-turbo'

        mock_file = Mock()
        mock_file.name = 'answer.wav'
        mock_file.read.return_value = b'audio-bytes'
        mock_file.content_type = 'audio/wav'

        post.return_value = Mock(status_code=200, json=lambda: {'text': 'This is my interview answer'})

        result = service.transcribe_audio(mock_file)
        self.assertEqual(result, 'This is my interview answer')


class TextToSpeechServiceTests(SimpleTestCase):
    def test_synthesize_raises_when_disabled(self):
        service = TextToSpeechService()
        service.enabled = False
        with self.assertRaisesMessage(Exception, "Cloud text-to-speech is disabled."):
            service.synthesize("Hello")

    def test_synthesize_returns_cached_audio(self):
        service = TextToSpeechService()
        service.enabled = True
        service.voice = 'test-voice'
        service.language_code = 'en-US'

        # Seed cache
        from hashlib import sha256
        cache_hash = sha256(f'test-voice:en-US:Hello'.encode()).hexdigest()
        cache.set(f'neural2_audio:{cache_hash}', b'fake-mp3-bytes', timeout=60)

        result = service.synthesize("Hello")
        self.assertEqual(result, b'fake-mp3-bytes')


class ResumeParserTests(SimpleTestCase):
    def setUp(self):
        self.parser = object.__new__(ResumeParser)
        self.parser.api_key = 'test-openrouter-key'
        self.parser.base_url = 'https://openrouter.ai/api/v1/chat/completions'
        self.parser.model = 'mistralai/mistral-7b-instruct'

    @staticmethod
    def response(payload, status_code=200):
        response = Mock(status_code=status_code)
        response.json.return_value = payload
        return response

    def test_empty_resume_text_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.parser.parse_resume_with_ai("   ")

    @patch('interview_core.resume_parser.requests.post')
    def test_successful_parsing_returns_structured_data(self, post):
        ai_payload = {
            'choices': [{
                'message': {
                    'content': '```json\n{"skills": ["Python", "Django"], "experience": ["Backend Dev"], "projects": ["API"]}\n```'
                }
            }]
        }
        post.return_value = self.response(ai_payload)

        data = self.parser.parse_resume_with_ai("Experienced Python Developer")
        self.assertEqual(data['skills'], ['Python', 'Django'])
        self.assertEqual(data['experience'], ['Backend Dev'])
        self.assertEqual(data['projects'], ['API'])

    @patch('interview_core.resume_parser.requests.post')
    def test_api_failure_raises_exception_instead_of_fake_data(self, post):
        post.return_value = self.response({'error': {'message': 'Quota exceeded'}}, status_code=429)

        with self.assertRaises(Exception) as ctx:
            self.parser.parse_resume_with_ai("Experienced Python Developer")
        self.assertIn("Quota exceeded", str(ctx.exception))

    @patch('interview_core.resume_parser.requests.post')
    def test_malformed_json_raises_exception(self, post):
        ai_payload = {
            'choices': [{
                'message': {
                    'content': 'Sorry, I cannot parse this.'
                }
            }]
        }
        post.return_value = self.response(ai_payload)

        with self.assertRaises(Exception):
            self.parser.parse_resume_with_ai("Experienced Python Developer")


from django.test import TestCase
from django.contrib.auth.models import User
from .services import InterviewService
from .models import InterviewQuestion


class InterviewServiceResumeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.service = object.__new__(InterviewService)
        self.service.question_service = Mock()
        self.service.ai_service = None
        self.service.audio_service = None

    def test_create_resume_questions_with_empty_categories_creates_fallback(self):
        questions = self.service.create_resume_questions(
            user=self.user,
            parsed_data={'skills': [], 'experience': [], 'projects': []},
            count=4,
            difficulty='medium'
        )
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].topic, 'Resume-Based')

    def test_create_resume_questions_generates_per_category(self):
        self.service.create_questions = Mock(side_effect=lambda user, topic, count, difficulty: [
            InterviewQuestion.objects.create(user=user, topic=topic, question=f"Q for {topic}", answer="A")
        ])
        parsed_data = {
            'skills': ['Python'],
            'experience': ['Django Dev'],
            'projects': ['Web app']
        }
        questions = self.service.create_resume_questions(
            user=self.user,
            parsed_data=parsed_data,
            count=3,
            difficulty='medium'
        )
        self.assertEqual(len(questions), 3)
        self.assertEqual(self.service.create_questions.call_count, 3)
