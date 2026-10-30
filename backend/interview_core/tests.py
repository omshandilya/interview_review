from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from .services import AIService


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
