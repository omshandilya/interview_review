# Interview Practice Platform - Backend

AI-powered interview preparation platform with speech recognition and feedback.

## Project Structure

```
backend/
├── backend/                    # Django project configuration
│   ├── __init__.py
│   ├── asgi.py                # ASGI configuration
│   ├── settings.py            # Django settings
│   ├── urls.py                # Main URL routing
│   └── wsgi.py                # WSGI configuration
├── interview_core/             # Main application
│   ├── management/
│   │   └── commands/
│   │       └── cleanup_old_files.py  # Audio cleanup command
│   ├── migrations/             # Database migrations
│   ├── admin.py               # Django admin configuration
│   ├── apps.py                # App configuration
│   ├── exceptions.py          # Custom exceptions
│   ├── models.py              # Database models
│   ├── serializers.py         # DRF serializers
│   ├── services.py            # Business logic services
│   ├── urls.py                # App URL routing
│   └── views.py               # API views
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── build.sh                   # Deployment script
├── db.sqlite3                 # SQLite database
├── manage.py                  # Django management script
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Features

- 🎯 AI-generated interview questions by topic
- 🎤 Audio answer recording and transcription
- 🤖 AI-powered answer evaluation and feedback
- 👤 User authentication with JWT
- 📚 Question bookmarking and progress tracking

## Setup

1. Create virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   copy .env.example .env
   # Edit .env with your API keys
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Start development server:
   ```bash
   python manage.py runserver
   ```

## API Endpoints

- `POST /register/` - User registration
- `POST /token/` - Login (JWT)
- `GET /questions/` - List questions
- `GET /generate-questions/<topic>/` - Generate new questions
- `POST /submit-answer/` - Submit audio answer
- `GET /report/` - User progress report
- `POST /save-question/` - Bookmark question
- `GET /saved-questions/` - List bookmarked questions

## Environment Variables

Required in `.env`:
- `OPENROUTER_API_KEY` - AI service API key
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (True/False)