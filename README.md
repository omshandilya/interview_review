# 🎯 Interview Review System

AI-powered interview practice platform with personalized questions, audio recording, and intelligent feedback.

## ✨ Features

- **🔐 User Authentication** - Secure JWT-based login system
- **🤖 AI Question Generation** - Topic-based and resume-based personalized questions
- **🎙️ Audio Recording** - Practice with real voice responses using Hugging Face Whisper
- **📊 Smart Feedback** - AI-powered answer analysis and scoring
- **💾 Question Management** - Save and review favorite questions
- **📱 Modern UI** - Dark theme with glassmorphism effects
- **📄 Resume Analysis** - Upload PDF/DOCX resumes for personalized interview questions
- **🗄️ Optimized Storage** - No permanent file storage, process-and-delete approach

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/interview-review.git
cd interview-review/backend

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

## 🔧 Environment Variables

```env
DJANGO_ENVIRONMENT=development
SECRET_KEY=your-secret-key
OPENROUTER_API_KEY=your-openrouter-api-key
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://... (for production)
```

## 🎯 Key Features Explained

### **Topic-Based Interviews**
- Select multiple topics (React, Python, System Design, etc.)
- Choose difficulty level (Easy, Medium, Hard)
- Generate 4-10 questions per session

### **Resume-Based Interviews**
- Upload PDF/DOCX resume files
- AI extracts skills, experience, and projects
- Generates personalized questions based on your background
- Resume data deleted after processing for privacy

### **Audio Practice**
- Record voice responses to questions
- Automatic transcription using Whisper-tiny model
- Get detailed feedback on your answers
- Scoring based on accuracy, clarity, and completeness

## 🌐 Deploy on Render

1. **Connect GitHub** to Render
2. **Create Web Service** with these settings:
   - Build Command: `./build.sh`
   - Start Command: `gunicorn backend.wsgi:application`
   - Root Directory: `backend`
3. **Add Environment Variables** in Render dashboard
4. **Create PostgreSQL** database and link it

## 🛠️ Tech Stack

- **Backend:** Django, Django REST Framework
- **Database:** SQLite (dev), PostgreSQL (prod)
- **AI:** OpenRouter API (GPT-3.5-turbo)
- **Audio:** Hugging Face Transformers (Whisper-tiny)
- **Document Processing:** PyPDF2, python-docx
- **Frontend:** Django Templates, Vanilla JS
- **Deployment:** Render, Gunicorn, WhiteNoise