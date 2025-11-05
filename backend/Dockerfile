# ---------- Base Image ----------
# Use a stable Python 3.10 image
FROM python:3.10-slim

# ---------- Set Work Directory ----------
WORKDIR /app

# ---------- Environment Variables ----------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---------- Install System Dependencies ----------
# Includes ffmpeg and libsndfile1 (used for Whisper/audio)
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

# ---------- Collect Static Files ----------
RUN python manage.py collectstatic --noinput || true

# ---------- Expose Port ----------
# Render sets $PORT automatically (default 10000)
EXPOSE 10000

# ---------- Run Migrations & Start Gunicorn ----------
# --noinput prevents Django from waiting for user input
# --timeout 180 ensures slow startups (e.g. transformers/torch) don’t fail
CMD python manage.py migrate --noinput && gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --timeout 180
