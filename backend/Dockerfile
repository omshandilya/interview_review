# ---------- Base Image ----------
# Use a stable Python 3.10 image
FROM python:3.10-slim

# ---------- Set Work Directory ----------
WORKDIR /app

# ---------- Environment Variables ----------
# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# ---------- Install System Dependencies ----------
# libsndfile1 and ffmpeg are useful for audio/Whisper-related features
RUN apt-get update && apt-get install -y \
    build-essential \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# ---------- Copy Project Files ----------
COPY . /app

# ---------- Install Python Dependencies ----------
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# ---------- Expose Port ----------
# Render expects apps to listen on port 10000
EXPOSE 10000

# ---------- Run Migrations & Start Server ----------
# When deploying on Render, this will start your Django app
CMD python manage.py migrate && gunicorn backend.wsgi:application --bind 0.0.0.0:10000
