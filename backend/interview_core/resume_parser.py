import os
import re
import json
import logging
import tempfile
import requests
import PyPDF2
import docx

logger = logging.getLogger(__name__)


class ResumeParser:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for resume parsing")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "mistralai/mistral-7b-instruct"

    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text.strip()
        except Exception as e:
            raise Exception(f"PDF extraction failed: {str(e)}")

    def extract_text_from_docx(self, file_path):
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"DOCX extraction failed: {str(e)}")

    def extract_text_from_resume(self, resume_file):
        """Extract text from resume file (PDF or DOCX)"""
        file_extension = resume_file.name.lower().split('.')[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
            for chunk in resume_file.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name

        try:
            if file_extension == 'pdf':
                text = self.extract_text_from_pdf(temp_path)
            elif file_extension == 'docx':
                text = self.extract_text_from_docx(temp_path)
            else:
                raise Exception("Unsupported file format")

            return text
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def parse_resume_with_ai(self, resume_text):
        """Use AI to parse resume and extract structured data"""
        if not resume_text or not resume_text.strip():
            raise ValueError("No readable text found in resume to analyze.")

        prompt = f"""
Analyze this resume and extract structured information. Return ONLY valid JSON in this exact format:

{{
    "skills": ["skill1", "skill2", "skill3"],
    "experience": ["experience1", "experience2"],
    "projects": ["project1", "project2"]
}}

Guidelines:
- skills: Technical skills, programming languages, frameworks, tools
- experience: Job roles, companies, domains, years of experience
- projects: Key projects, achievements, technologies used

Resume text:
{resume_text}

Return only the JSON object, no other text.
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }

        content = None
        for attempt in range(2):
            try:
                response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            except requests.exceptions.RequestException as exc:
                if attempt == 0:
                    logger.warning("Resume parsing request failed; retrying once: %s", str(exc))
                    continue
                raise Exception("Failed to connect to AI service for resume parsing") from exc

            if response.status_code != 200:
                error_detail = f"status {response.status_code}"
                try:
                    err_json = response.json().get('error')
                    if isinstance(err_json, dict) and err_json.get('message'):
                        error_detail = err_json['message']
                    elif isinstance(err_json, str):
                        error_detail = err_json
                except Exception:
                    pass

                if attempt == 0 and response.status_code >= 500:
                    logger.warning("AI service returned %s; retrying once.", error_detail)
                    continue
                raise Exception(f"AI service request failed: {error_detail}")

            try:
                response_data = response.json()
                content = response_data['choices'][0]['message'].get('content')
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                if attempt == 0:
                    logger.warning("AI service returned an invalid response structure; retrying once.")
                    continue
                raise Exception("AI service returned an invalid response structure") from exc

            if isinstance(content, str) and content.strip():
                break

            if attempt == 0:
                logger.warning("AI service returned empty content; retrying once.")
                continue
            raise Exception("AI service returned an empty completion for resume parsing.")

        cleaned_response = content.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]
        elif cleaned_response.startswith('```'):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        parsed_data = None
        try:
            parsed_data = json.loads(cleaned_response)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if match:
                try:
                    parsed_data = json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        if not isinstance(parsed_data, dict):
            raise Exception("Failed to parse valid JSON data from AI response.")

        skills = parsed_data.get('skills', [])
        experience = parsed_data.get('experience', [])
        projects = parsed_data.get('projects', [])

        if not isinstance(skills, list):
            skills = [str(skills)] if skills else []
        if not isinstance(experience, list):
            experience = [str(experience)] if experience else []
        if not isinstance(projects, list):
            projects = [str(projects)] if projects else []

        if not (skills or experience or projects):
            raise Exception("Could not extract any skills, experience, or projects from the resume.")

        return {
            "skills": [str(s).strip() for s in skills if s],
            "experience": [str(e).strip() for e in experience if e],
            "projects": [str(p).strip() for p in projects if p]
        }

    def process_resume(self, resume_file):
        """Complete resume processing pipeline"""
        extracted_text = self.extract_text_from_resume(resume_file)
        if not extracted_text or not extracted_text.strip():
            raise Exception("Could not extract readable text from the resume. Please ensure the document is not an image scan.")

        parsed_data = self.parse_resume_with_ai(extracted_text)

        return {
            'extracted_text': extracted_text,
            'skills': parsed_data.get('skills', []),
            'experience': parsed_data.get('experience', []),
            'projects': parsed_data.get('projects', [])
        }
