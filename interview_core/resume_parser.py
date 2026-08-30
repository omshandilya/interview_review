import PyPDF2
import docx
import json
import requests
import os
# from django.core.files.storage import default_storage  # Not needed anymore

class ResumeParser:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "mistralai/mistral-7b-instruct"
    
    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            raise Exception(f"PDF extraction failed: {str(e)}")
    
    def extract_text_from_docx(self, file_path):
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"DOCX extraction failed: {str(e)}")
    
    def extract_text_from_resume(self, resume_file):
        """Extract text from resume file (PDF or DOCX)"""
        import tempfile
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{resume_file.name.split(".")[-1]}') as temp_file:
            # Write file content to temp file
            for chunk in resume_file.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        try:
            file_extension = resume_file.name.lower().split('.')[-1]
            
            if file_extension == 'pdf':
                text = self.extract_text_from_pdf(temp_path)
            elif file_extension == 'docx':
                text = self.extract_text_from_docx(temp_path)
            else:
                raise Exception("Unsupported file format")
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            return text
        except Exception as e:
            # Ensure cleanup even on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
    
    def parse_resume_with_ai(self, resume_text):
        """Use AI to parse resume and extract structured data"""
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
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "http://localhost",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"AI API request failed: {response.status_code}")
            
            ai_response = response.json()['choices'][0]['message']['content']
            
            # Try to parse JSON from response
            try:
                # Clean the response and extract JSON
                cleaned_response = ai_response.strip()
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response.replace('```json', '').replace('```', '')
                
                parsed_data = json.loads(cleaned_response)
                
                # Validate structure
                if not all(key in parsed_data for key in ['skills', 'experience', 'projects']):
                    raise ValueError("Missing required keys")
                
                return parsed_data
                
            except (json.JSONDecodeError, ValueError):
                # Fallback: return basic structure
                return {
                    "skills": ["General Programming", "Problem Solving"],
                    "experience": ["Software Development"],
                    "projects": ["Various Projects"]
                }
                
        except Exception as e:
            # Fallback parsing
            return {
                "skills": ["General Programming", "Problem Solving"],
                "experience": ["Software Development"],
                "projects": ["Various Projects"]
            }
    
    def process_resume(self, resume_file):
        """Complete resume processing pipeline"""
        # Extract text
        extracted_text = self.extract_text_from_resume(resume_file)
        
        # Parse with AI
        parsed_data = self.parse_resume_with_ai(extracted_text)
        
        return {
            'extracted_text': extracted_text,
            'skills': parsed_data.get('skills', []),
            'experience': parsed_data.get('experience', []),
            'projects': parsed_data.get('projects', [])
        }