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
GROQ_API_KEY=your-groq-api-key
# Optional: defaults to openai/gpt-oss-20b
GROQ_QUESTION_MODEL=openai/gpt-oss-20b
# Required only for answer evaluation and resume parsing
OPENROUTER_API_KEY=your-openrouter-api-key
GOOGLE_TTS_ENABLED=true
# Configure either a credential-file path or service-account JSON in your host's secret store.
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
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

### **Question narration (Google Neural2)**

Interview questions use Google Cloud Text-to-Speech's Neural2 voice when it is configured. Enable the Cloud Text-to-Speech API, create a service account with the **Cloud Text-to-Speech User** role, and set `GOOGLE_APPLICATION_CREDENTIALS` to its JSON credential path. On platforms that only support text secrets, set `GOOGLE_APPLICATION_CREDENTIALS_JSON` to the complete JSON key instead. `GOOGLE_TTS_VOICE` defaults to `en-IN-Neural2-A`; set it to any compatible Neural2 voice to change the narrator. If the service, credentials, or network are unavailable, the app automatically uses the browser's native speech voice.

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
- **AI question generation:** Groq API (GPT-OSS 20B by default)
- **Audio:** Hugging Face Transformers (Whisper-tiny)
- **Document Processing:** PyPDF2, python-docx
- **Frontend:** Django Templates, Vanilla JS
- **Deployment:** Render, Gunicorn, WhiteNoise
