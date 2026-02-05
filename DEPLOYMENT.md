# PolicyPulse - Deployment Guide

## 🚀 Deploying to Render.com (Recommended - FREE)

### Prerequisites
- GitHub account
- Render.com account (free tier)
- (Optional) API keys for enhanced features

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/USERNAME/PolicyPulse.git
git push -u origin main
```

### Step 2: Deploy on Render
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will detect `render.yaml` automatically
5. Click **"Apply"**

### Step 3: Configure Environment Variables (Optional)
In Render dashboard, go to your service → Environment:

- **GEMINI_API_KEY**: Your Gemini API key (free tier)
- **GOOGLE_CLOUD_TRANSLATE_KEY**: Google Translation API key
- **TWILIO_ACCOUNT_SID**: Twilio account SID
- **TWILIO_AUTH_TOKEN**: Twilio auth token
- **TWILIO_PHONE_NUMBER**: Your Twilio phone number

### Step 4: Wait for Deployment
- Build time: ~5-10 minutes
- Render will run `pip install` + data ingestion automatically
- Check logs for any errors

### Step 5: Access Your App
- URL: `https://policypulse.onrender.com` (or your chosen name)
- Test endpoints:
  - `GET /health` - Health check
  - `GET /` - Main UI
  - `GET /docs` - API documentation

---

## 🔧 Alternative: Fly.io Deployment

### Prerequisites
- Install flyctl: `curl -L https://fly.io/install.sh | sh`
- Sign up: `flyctl auth signup`

### Deploy
```bash
# Initialize Fly app
flyctl launch

# Deploy
flyctl deploy

# Open app
flyctl open
```

---

## 💻 Local Deployment

### Setup (Windows)
```bash
./setup.bat
```

### Setup (Linux/Mac)
```bash
chmod +x setup.sh
./setup.sh
```

### Start Server
```bash
python start.py
```

### Access
- URL: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🔑 Getting API Keys (All Free Tier)

### 1. Gemini API (Recommended)
1. Go to: https://makersuite.google.com/app/apikey
2. Sign in with Gmail
3. Click "Create API Key"
4. Copy key → Add to Render environment or `.env`

**Limits**: 15 requests/min, 1500/day (FREE forever)

### 2. Google Cloud Translation (Optional)
1. Go to: https://console.cloud.google.com/
2. Create project
3. Enable "Cloud Translation API"
4. Create Credentials → API Key
5. Copy key

**Limits**: 500,000 characters/month (FREE)

### 3. Twilio (Optional - for WhatsApp/SMS)
1. Go to: https://www.twilio.com/try-twilio
2. Sign up (phone verification required)
3. Get $15 free credit (~100 SMS)
4. Copy: Account SID, Auth Token, Phone Number

---

## 🧪 Testing Your Deployment

### Health Check
```bash
curl https://your-app.onrender.com/health
```

### Test Query
```bash
curl -X POST https://your-app.onrender.com/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "What is NREGA?", "language": "en"}'
```

### Test Eligibility
```bash
curl -X POST https://your-app.onrender.com/eligibility/check \
  -H "Content-Type: application/json" \
  -d '{"age": 30, "occupation": "farmer", "location_type": "rural", "income": 50000}'
```

---

## 🐛 Troubleshooting

### Build Fails
- Check Python version (must be 3.11+)
- Verify `requirements.txt` is complete
- Check Render logs for specific errors

### Data Ingestion Fails
- Ensure `Data/` directory is pushed to GitHub
- Check file permissions
- Verify CSV files are valid

### API Errors
- Check environment variables are set correctly
- Verify ChromaDB initialized (check logs)
- Test locally first: `python start.py`

### Out of Memory
- Render free tier: 512MB RAM
- If hitting limits, reduce batch sizes in `cli.py`
- Or upgrade to Render's paid tier ($7/month for 2GB RAM)

---

## 📊 Monitoring

### Render Dashboard
- View logs: Services → Logs
- Check metrics: Services → Metrics
- Restart service: Services → Manual Deploy

### API Endpoints for Monitoring
- `/health` - Service status
- `/stats` - Database & performance stats

---

## 🔄 Updating Your Deployment

### With Render (Auto-deploy)
```bash
git add .
git commit -m "Update message"
git push origin main
```
Render will automatically rebuild and redeploy!

### Manual Trigger
- Render Dashboard → Manual Deploy → Deploy latest commit

---

## 💰 Cost Breakdown

| Service | Free Tier | Paid (Optional) |
|---------|-----------|----------------|
| **Render.com** | ✅ FREE | $7/month (more RAM) |
| **ChromaDB** | ✅ FREE (local storage) | - |
| **Gemini API** | ✅ FREE (1500 req/day) | - |
| **Google Translate** | ✅ FREE (500K chars/month) | $20/1M chars |
| **Twilio** | $15 credit (~100 SMS) | Pay as you go |

**Recommended setup: 100% FREE** (use free tiers only)

---

## 🎯 Ready to Deploy?

1. Push code to GitHub
2. Connect to Render.com
3. Add optional API keys
4. Deploy!
5. Share with your community 🚀

Need help? Check `/docs` endpoint for API documentation.
