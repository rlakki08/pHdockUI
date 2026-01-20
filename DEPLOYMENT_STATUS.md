# pHdockUI - Deployment Status

## ✅ Current Configuration

### Frontend (Local Development)
- **URL:** http://localhost:3000
- **Status:** ✅ Running
- **Framework:** Next.js 15.4.10
- **Backend Connection:** Railway (production)

### Backend (Railway Production)
- **URL:** https://phdock-production.up.railway.app
- **Status:** ✅ Healthy
- **Health Check:** `/health` endpoint responding
- **Framework:** FastAPI + Python

---

## 🌐 Architecture

```
┌─────────────────────────┐
│  Frontend (localhost)   │
│   Next.js on :3000      │
│                         │
│  .env.local configured  │
└───────────┬─────────────┘
            │
            │ API Calls
            │ (NEXT_PUBLIC_API_URL)
            ▼
┌─────────────────────────┐
│  Backend (Railway)      │
│  phdock-production      │
│  .up.railway.app        │
│                         │
│  FastAPI + Python       │
│  RDKit, ML Models       │
│  GNINA Integration      │
└─────────────────────────┘
```

---

## 🔧 Configuration Files

### Frontend Environment
**File:** `website/.env.local`
```bash
BACKEND_URL=https://phdock-production.up.railway.app
NEXT_PUBLIC_API_URL=https://phdock-production.up.railway.app
```

### Backend Railway Config
**File:** `website/backend/railway.json`
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "website/backend/Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

---

## 🚀 Deployment Modes

### Mode 1: Local Frontend + Railway Backend (Current)
**Best for:** Local development while using production ML models

```bash
# Frontend (local)
cd website
npm run dev

# Backend (Railway)
# Already deployed - no action needed
```

**Access:**
- Frontend: http://localhost:3000
- Backend: https://phdock-production.up.railway.app

### Mode 2: Fully Local
**Best for:** Offline development, testing new backend features

```bash
# Create local env
cd website
cat > .env.local << EOF
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

# Start both services
npm run dev &
cd ../website/backend && uvicorn main:app --reload &
```

**Access:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

### Mode 3: Fully Deployed (Production)
**Best for:** Public access

```bash
# Deploy frontend to Vercel
vercel deploy --prod

# Backend already on Railway
# Update frontend env in Vercel dashboard:
# NEXT_PUBLIC_API_URL=https://phdock-production.up.railway.app
```

**Access:**
- Frontend: https://your-app.vercel.app
- Backend: https://phdock-production.up.railway.app

---

## 📊 Railway Backend Status

### Health Check
```bash
curl https://phdock-production.up.railway.app/health
```

**Response:**
```json
{
  "status": "healthy",
  "modules_available": true
}
```

### Available Endpoints

#### Standard Endpoints
```
GET  /health                    - Health check
GET  /docs                      - API documentation (Swagger)
GET  /redoc                     - API documentation (ReDoc)

POST /api/jobs                  - Submit docking job
GET  /api/jobs/{id}             - Get job status
GET  /api/jobs/{id}/result      - Get job results

GET  /api/receptors             - List receptors
GET  /api/receptors/search      - Search PDB database
GET  /api/receptors/{id}        - Get receptor details
GET  /api/receptors/{id}/pdb    - Download receptor PDB
```

#### pH-Ensemble Endpoints (NEW - if deployed)
```
POST /api/ensemble-docking      - pH-aware ensemble docking
GET  /api/ensemble/{id}         - Get ensemble results
GET  /api/titration-curve       - Generate pH titration curve
POST /api/microstate-enum       - Enumerate microstates
```

---

## 🔄 Deploying pH-Ensemble to Railway

### Step 1: Update Backend Code

The backend needs to include the new pH-ensemble endpoints. Check if these files exist on Railway:

```
website/backend/
├── main.py                    (updated with ensemble routes)
├── requirements.txt           (includes new dependencies)
└── Dockerfile                 (builds with RDKit)
```

### Step 2: Push to Railway

```bash
# If Railway is connected to GitHub
git push origin main

# Railway auto-deploys from main branch
```

### Step 3: Verify Deployment

```bash
# Check health
curl https://phdock-production.up.railway.app/health

# Check new endpoints
curl https://phdock-production.up.railway.app/docs
# Look for /api/ensemble-docking endpoint
```

### Step 4: Update Backend Requirements

Ensure `website/backend/requirements.txt` includes:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
rdkit==2023.9.2
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
# ... other dependencies
```

---

## 🧪 Testing the Integration

### Test 1: Frontend → Railway Backend

```bash
# Open browser
open http://localhost:3000

# Submit a job
# Enter SMILES: CC(=O)O
# Click "Run Docking"

# Check browser network tab
# Requests should go to:
# https://phdock-production.up.railway.app/api/jobs
```

### Test 2: Direct API Call

```bash
# Test job submission
curl -X POST https://phdock-production.up.railway.app/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "smiles": "CC(=O)O",
    "ph_value": 7.4,
    "conformer_count": 10
  }'

# Should return:
{
  "job_id": "abc123",
  "status": "queued"
}
```

### Test 3: pH-Ensemble (if deployed)

```bash
curl -X POST https://phdock-production.up.railway.app/api/ensemble-docking \
  -H "Content-Type: application/json" \
  -d '{
    "smiles": "CC(=O)O",
    "target_ph": 7.4,
    "probability_threshold": 0.01
  }'
```

---

## 📈 Monitoring

### Railway Dashboard
- **URL:** https://railway.app/dashboard
- **Metrics:** CPU, Memory, Network, Logs
- **Logs:** Real-time application logs

### Health Monitoring Script

```bash
#!/bin/bash
# monitor.sh

while true; do
  STATUS=$(curl -s https://phdock-production.up.railway.app/health | jq -r '.status')
  if [ "$STATUS" == "healthy" ]; then
    echo "✅ $(date): Backend healthy"
  else
    echo "❌ $(date): Backend unhealthy!"
  fi
  sleep 60
done
```

---

## 🐛 Troubleshooting

### Frontend Can't Reach Backend

**Symptom:** CORS errors, connection refused

**Check:**
```bash
# Verify env variables loaded
cat website/.env.local

# Restart frontend
pkill -f "next dev"
cd website && npm run dev
```

**Solution:**
- Ensure `.env.local` exists with Railway URL
- Check Railway backend is healthy
- Verify CORS settings in Railway backend

### Railway Backend Down

**Check:**
```bash
curl https://phdock-production.up.railway.app/health
```

**Actions:**
1. Check Railway dashboard for errors
2. View application logs
3. Restart service in Railway dashboard
4. Check build logs for deployment issues

### New Code Not Deployed

**Issue:** Pushed code but Railway still running old version

**Solution:**
1. Check Railway GitHub integration
2. Manual redeploy in Railway dashboard
3. Check build logs for errors
4. Verify `railway.json` configuration

---

## 📦 What's Deployed vs Local

### Currently Deployed on Railway (likely older version)
- Basic docking endpoints
- pKa prediction
- Receptor search
- Job management

### New Features (Local Only - Need Deployment)
- ✨ `src/thermodynamics.py` module
- ✨ pH-ensemble docking pipeline
- ✨ Microstate enumeration with probabilities
- ✨ Ensemble aggregation endpoints

---

## 🚀 Next Steps to Deploy pH-Ensemble

### 1. Prepare Backend Files

Ensure these files in `website/backend/` include pH-ensemble code:
- [ ] `main.py` - Add ensemble endpoints
- [ ] Copy `../../src/thermodynamics.py` to backend
- [ ] Copy `../../src/protonation_engine.py` (updated)
- [ ] Copy `../../src/docking_integration.py` (updated)
- [ ] Update `requirements.txt`

### 2. Push to Railway

```bash
git add website/backend/
git commit -m "feat: add pH-ensemble endpoints to backend"
git push origin main
```

### 3. Verify Deployment

```bash
# Check health
curl https://phdock-production.up.railway.app/health

# Check docs for new endpoints
open https://phdock-production.up.railway.app/docs
```

### 4. Test from Frontend

Open http://localhost:3000 and test the new pH-ensemble features!

---

## 📊 Current Status Summary

| Component | Status | URL | Version |
|-----------|--------|-----|---------|
| Frontend | ✅ Local | http://localhost:3000 | Latest |
| Backend | ✅ Railway | https://phdock-production.up.railway.app | Production |
| pH-Ensemble Module | ✅ Local | - | Implemented |
| pH-Ensemble Backend | ⏸️ Pending Deploy | - | Not yet deployed |

**Next Action:** Deploy pH-ensemble code to Railway backend

---

## 🎯 Quick Reference

**Health Check:**
```bash
curl https://phdock-production.up.railway.app/health
```

**View API Docs:**
```bash
open https://phdock-production.up.railway.app/docs
```

**Local Frontend:**
```bash
cd website && npm run dev
```

**View Logs:**
- Railway Dashboard → Select Project → Deployments → View Logs
