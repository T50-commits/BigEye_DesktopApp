# BigEye Pro — Deployment & Infrastructure Guide
### Google Cloud Platform Setup
### Date: February 2026

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     GOOGLE CLOUD PROJECT                         │
│                     "bigeye-pro-prod"                             │
│                                                                   │
│  ┌─────────────────┐    ┌──────────────────┐                     │
│  │  Cloud Run       │    │  Firestore        │                    │
│  │  "bigeye-api"    │◄──►│  (Native Mode)    │                    │
│  │  FastAPI          │    │  6 collections    │                    │
│  │  Port 8080        │    └──────────────────┘                    │
│  │  Min: 0, Max: 10  │                                            │
│  └────────┬──────────┘    ┌──────────────────┐                    │
│           │               │  Cloud Storage    │                    │
│           │               │  "bigeye-slips"   │                    │
│           │               │  Slip images       │                   │
│           │               └──────────────────┘                    │
│  ┌────────┴──────────┐                                            │
│  │  Cloud Scheduler   │    ┌──────────────────┐                    │
│  │  2 jobs:           │    │  Secret Manager   │                   │
│  │  - cleanup (1h)    │    │  JWT_SECRET        │                   │
│  │  - daily_report    │    │  AES_KEY           │                   │
│  │    (midnight)      │    │  SLIP_API_KEY      │                   │
│  └───────────────────┘    └──────────────────┘                    │
│                                                                   │
│  ┌───────────────────┐                                            │
│  │  Cloud Run          │   (Optional — Phase 2)                    │
│  │  "admin-dashboard"  │                                           │
│  │  Streamlit           │                                           │
│  └───────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘

          ▲                              ▲
          │ HTTPS                         │ gRPC
          │                              │
┌─────────┴──────────┐      ┌───────────┴────────────┐
│  Desktop Client     │      │  Google Gemini API      │
│  PySide6 + Nuitka   │      │  (Client's own key)     │
│  Windows .exe        │      │  gemini-2.5-pro etc.    │
└────────────────────┘      └────────────────────────┘
```

---

## 2. Prerequisites

| Item | Details |
|:--|:--|
| GCP Account | With billing enabled |
| gcloud CLI | Installed and authenticated |
| Domain (optional) | e.g. `api.bigeye.pro` |
| LINE Notify Token | For admin notifications |
| Slip Verification API Key | SlipOK or EasySlip account |

---

## 3. Step-by-Step Setup

### 3.1 Create GCP Project

```bash
# Create project
gcloud projects create bigeye-pro-prod --name="BigEye Pro"
gcloud config set project bigeye-pro-prod

# Enable billing (do in console)
# https://console.cloud.google.com/billing

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com
```

### 3.2 Setup Firestore

```bash
# Create Firestore database (Native mode, asia-southeast1 for Thailand)
gcloud firestore databases create --location=asia-southeast1

# Create composite indexes (run after first deploy)
gcloud firestore indexes composite create \
  --collection-group=users \
  --field-config field-path=status,order=ASCENDING \
  --field-config field-path=last_active,order=DESCENDING

gcloud firestore indexes composite create \
  --collection-group=jobs \
  --field-config field-path=status,order=ASCENDING \
  --field-config field-path=expires_at,order=ASCENDING

gcloud firestore indexes composite create \
  --collection-group=transactions \
  --field-config field-path=user_id,order=ASCENDING \
  --field-config field-path=created_at,order=DESCENDING

gcloud firestore indexes composite create \
  --collection-group=audit_logs \
  --field-config field-path=severity,order=ASCENDING \
  --field-config field-path=created_at,order=DESCENDING
```

### 3.3 Setup Secret Manager

```bash
# Store secrets (replace values)
echo -n "your-jwt-secret-key-min-32-chars" | \
  gcloud secrets create JWT_SECRET --data-file=-

echo -n "your-aes-256-key-hex-64-chars" | \
  gcloud secrets create AES_KEY --data-file=-

echo -n "your-slip-api-key" | \
  gcloud secrets create SLIP_API_KEY --data-file=-

echo -n "your-line-notify-token" | \
  gcloud secrets create LINE_NOTIFY_TOKEN --data-file=-
```

### 3.4 Setup Cloud Storage (for slip images)

```bash
# Create bucket
gsutil mb -l asia-southeast1 gs://bigeye-slips

# Set lifecycle (delete after 90 days)
cat > lifecycle.json << 'EOF'
{
  "rule": [{
    "action": {"type": "Delete"},
    "condition": {"age": 90}
  }]
}
EOF
gsutil lifecycle set lifecycle.json gs://bigeye-slips
```

### 3.5 Deploy Backend API to Cloud Run

```bash
cd backend/

# Build and deploy
gcloud run deploy bigeye-api \
  --source . \
  --region asia-southeast1 \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 10 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --set-env-vars "ENVIRONMENT=production" \
  --set-secrets "JWT_SECRET=JWT_SECRET:latest,AES_KEY=AES_KEY:latest,SLIP_API_KEY=SLIP_API_KEY:latest,LINE_NOTIFY_TOKEN=LINE_NOTIFY_TOKEN:latest"
```

**Expected output:**
```
Service [bigeye-api] revision [bigeye-api-00001] has been deployed
Service URL: https://bigeye-api-xxxxx-as.a.run.app
```

### 3.6 Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service bigeye-api \
  --domain api.bigeye.pro \
  --region asia-southeast1

# Add DNS records as instructed by gcloud output
# Then verify:
curl https://api.bigeye.pro/api/v1/system/health
```

### 3.7 Setup Cloud Scheduler

```bash
# Get the Cloud Run service URL
SERVICE_URL=$(gcloud run services describe bigeye-api \
  --region asia-southeast1 --format 'value(status.url)')

# Job 1: Cleanup expired jobs (every hour)
gcloud scheduler jobs create http bigeye-cleanup \
  --location asia-southeast1 \
  --schedule "0 * * * *" \
  --uri "${SERVICE_URL}/api/v1/system/cleanup-expired-jobs" \
  --http-method POST \
  --oidc-service-account-email \
    $(gcloud iam service-accounts list --format 'value(email)' --filter 'displayName:Compute')

# Job 2: Daily report (midnight Bangkok time, UTC+7)
gcloud scheduler jobs create http bigeye-daily-report \
  --location asia-southeast1 \
  --schedule "0 17 * * *" \
  --time-zone "Asia/Bangkok" \
  --uri "${SERVICE_URL}/api/v1/system/generate-daily-report" \
  --http-method POST \
  --oidc-service-account-email \
    $(gcloud iam service-accounts list --format 'value(email)' --filter 'displayName:Compute')
```

### 3.8 Initialize Firestore Data

```bash
# Run initialization script (creates system_config document)
cd backend/
python -m app.scripts.init_firestore
```

This script should create:
- `system_config/app_settings` document with default prompts, rates, blacklist
- First admin user (if needed)

---

## 4. Environment Variables

### Backend (.env for local dev)

```env
# Firebase
GOOGLE_APPLICATION_CREDENTIALS=./firebase-service-account.json

# Security
JWT_SECRET=your-jwt-secret-key-min-32-chars-long
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=168
AES_KEY=your-aes-256-key-hex-64-chars

# External APIs
SLIP_VERIFY_URL=https://api.slipok.com/api/line/apikey/XXX
SLIP_API_KEY=your-slip-api-key

# Notifications
LINE_NOTIFY_TOKEN=your-line-notify-token

# App
ENVIRONMENT=development
ADMIN_UIDS=uid1,uid2
```

### Client (client/core/config.py)

```python
APP_VERSION = "2.0.0"
BACKEND_URL = "https://api.bigeye.pro"  # Production
# BACKEND_URL = "http://localhost:8000"  # Development
AES_KEY_HEX = "same-key-as-backend-64-hex-chars"
```

---

## 5. CI/CD Pipeline (Optional)

### GitHub Actions for Backend

```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloud Run
on:
  push:
    branches: [main]
    paths: [backend/**]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_CREDENTIALS }}
      - uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: bigeye-api
          region: asia-southeast1
          source: backend/
```

### Nuitka Build for Client (manual)

```bash
cd client/
pip install nuitka
python build/build_nuitka.py
# Output: dist/BigEyePro.exe
```

---

## 6. Monitoring & Alerts

### 6.1 Cloud Run Monitoring

GCP Console → Cloud Run → bigeye-api → Metrics:
- Request count
- Request latency (P50, P95, P99)
- Error rate
- Instance count
- Memory/CPU usage

### 6.2 Alert Policies

```bash
# Create alert: Error rate > 5%
gcloud monitoring policies create \
  --display-name "BigEye API Error Rate" \
  --condition-display-name "Error rate > 5%" \
  --condition-filter 'resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.labels.response_code_class="5xx"' \
  --notification-channels "projects/bigeye-pro-prod/notificationChannels/CHANNEL_ID"
```

### 6.3 Log Explorer

```
# View error logs
resource.type="cloud_run_revision"
severity>=ERROR

# View auth failures
resource.type="cloud_run_revision"
jsonPayload.event_type="LOGIN_FAILED_DEVICE_MISMATCH"
```

---

## 7. Cost Estimate

### Monthly costs at different scales:

| Service | 200 Users | 500 Users | 1,000 Users |
|:--|:-:|:-:|:-:|
| Cloud Run | Free | ~$5 | ~$15 |
| Firestore Reads | Free | ~$0.50 | ~$3 |
| Firestore Writes | Free | Free | ~$1 |
| Cloud Storage | Free | ~$0.10 | ~$0.50 |
| Cloud Scheduler | Free | Free | Free |
| Secret Manager | Free | Free | Free |
| **Total** | **~$0** | **~$6** | **~$20** |

**Revenue breakeven:** At 1 THB = 4 credits, 3 cr/file for iStock:
- 200 users × 50 files/month average = ₿2,500/month revenue
- Cost: ~$0/month → **100% margin at small scale**

---

## 8. Backup Strategy

### Firestore Export (Weekly)

```bash
# Manual export
gcloud firestore export gs://bigeye-backups/$(date +%Y%m%d)

# Automated via Cloud Scheduler (weekly Sunday 3AM)
gcloud scheduler jobs create http bigeye-backup \
  --location asia-southeast1 \
  --schedule "0 20 * * SUN" \
  --uri "https://firestore.googleapis.com/v1/projects/bigeye-pro-prod/databases/(default)/documents:exportDocuments" \
  --http-method POST \
  --message-body '{"outputUriPrefix":"gs://bigeye-backups"}' \
  --oauth-service-account-email PROJECT_NUMBER-compute@developer.gserviceaccount.com
```

### Restore

```bash
gcloud firestore import gs://bigeye-backups/20260207
```

---

## 9. Security Checklist

| # | Item | Status |
|:-:|:--|:-:|
| 1 | HTTPS only (Cloud Run enforces) | ✅ |
| 2 | JWT tokens with expiry | ✅ |
| 3 | Passwords hashed with bcrypt | ✅ |
| 4 | Firestore Security Rules deployed | ☐ |
| 5 | Rate limiting on auth endpoints | ✅ |
| 6 | Secrets in Secret Manager (not env) | ✅ |
| 7 | Hardware ID binding | ✅ |
| 8 | AES-256 for prompt encryption | ✅ |
| 9 | Slip images lifecycle (90-day delete) | ✅ |
| 10 | Firestore weekly backups | ☐ |
| 11 | Cloud Run min-instances: 0 | ✅ |
| 12 | No sensitive data in client binary | ✅ |

---

## 10. Deployment Checklist (Go-Live)

```
PRE-LAUNCH:
☐ GCP project created with billing
☐ All APIs enabled
☐ Firestore database created (asia-southeast1)
☐ Firestore indexes created
☐ Firestore security rules deployed
☐ Secret Manager secrets set
☐ Cloud Storage bucket created with lifecycle
☐ Backend deployed to Cloud Run
☐ Health check passes: GET /api/v1/system/health
☐ Cloud Scheduler jobs created (cleanup + daily report)
☐ system_config initialized in Firestore
☐ Prompts uploaded and encrypted
☐ Blacklist populated
☐ LINE Notify connected and tested

CLIENT:
☐ config.py BACKEND_URL set to production
☐ config.py AES_KEY_HEX matches backend
☐ Nuitka build succeeds
☐ .exe runs and connects to production API
☐ Register → Login → Top-up → Process flow works end-to-end

POST-LAUNCH:
☐ Monitor Cloud Run metrics for first 24h
☐ Verify daily report generated
☐ Verify expired job cleanup works
☐ Test backup/restore procedure
☐ Set up alerting policies
```

---

*Deployment & Infrastructure Guide — Complete GCP setup for BigEye Pro*
