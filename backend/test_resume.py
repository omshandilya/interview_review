#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from interview_core.resume_parser import ResumeParser

def test_resume_parser():
    """Test resume parser with a simple text file"""
    
    # Create a simple test file
    test_content = """
John Doe
Software Engineer

Skills:
- Python
- Django
- JavaScript
- React

Experience:
- Software Developer at ABC Company (2020-2023)
- Junior Developer at XYZ Corp (2018-2020)

Projects:
- E-commerce website using Django and React
- Mobile app with React Native
"""
    
    # Write test content to a temporary file
    with open('test_resume.txt', 'w') as f:
        f.write(test_content)
    
    print("Test file created")
    
    # Test AI parsing
    parser = ResumeParser()
    try:
        result = parser.parse_resume_with_ai(test_content)
        print("AI parsing successful:")
        print(f"Skills: {result['skills']}")
        print(f"Experience: {result['experience']}")
        print(f"Projects: {result['projects']}")
    except Exception as e:
        print(f"AI parsing failed: {e}")
    
    # Cleanup
    if os.path.exists('test_resume.txt'):
        os.remove('test_resume.txt')

if __name__ == "__main__":
    test_resume_parser()