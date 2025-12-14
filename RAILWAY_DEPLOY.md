# 🚂 Railway Deployment Guide

## ✅ What I Fixed

1. **Created Railway config files** (Procfile, railway.json, nixpacks.toml)
2. **Optimized memory usage** - Lazy loading Whisper model (saves ~200MB)
3. **Added memory cleanup** - Garbage collection after transcription

## 🚀 Deploy to Railway

### Step 1: Push Changes to GitHub
```bash
git add .
git commit -m "Add Railway config and optimize memory"
git push origin main
```

### Step 2: Railway Setup

1. Go to [railway.app](https://railway.app)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your `interview_review_deployed` repository
4. Railway will auto-detect Django and start building

### Step 3: Add Environment Variables

In Railway dashboard, go to **Variables** tab and add:

```
DJANGO_ENVIRONMENT=production
SECRET_KEY=your-secret-key-here-make-it-long-and-random
OPENROUTER_API_KEY=your-openrouter-api-key
ALLOWED_HOSTS=.railway.app
DISABLE_COLLECTSTATIC=1
```

### Step 4: Add PostgreSQL Database

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway will automatically set `DATABASE_URL` variable

### Step 5: Deploy

Railway will automatically deploy. Check the **Deployments** tab for progress.

## 🔧 If Build Fails

If you see errors, try these commands in Railway's **Settings** → **Deploy**:

**Build Command:**
```bash
cd backend && pip install -r requirements.txt && python manage.py collectstatic --noinput
```

**Start Command:**
```bash
cd backend && gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
```

## 💰 Cost

- **First $5 free** (credit)
- **~$5/month** after that for 512MB RAM
- Scales automatically if you need more

## 🎯 Expected Performance

- **10-20 users**: Works perfectly
- **Memory usage**: ~300-400MB (optimized)
- **Response time**: Fast (Whisper loads only when needed)

## ✅ Verify Deployment

Once deployed, Railway gives you a URL like: `https://your-app.railway.app`

Test it:
1. Visit the URL
2. Register/Login
3. Try generating questions
4. Test audio recording

## 🐛 Troubleshooting

**Still out of memory?**
- Upgrade to 1GB plan ($10/month) in Railway settings
- Or disable audio transcription temporarily

**Database errors?**
- Make sure PostgreSQL is added and connected
- Check `DATABASE_URL` is set automatically

**Static files not loading?**
- Check `DISABLE_COLLECTSTATIC=1` is NOT set
- Or run: `python manage.py collectstatic` in Railway console

## 📞 Need Help?

Check Railway logs in the **Deployments** tab for detailed error messages.
