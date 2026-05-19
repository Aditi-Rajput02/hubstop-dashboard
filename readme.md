# CRM Sequence Automator — Full Stack Dashboard

## 🚀 TL;DR — Run the App in One Command

**Windows:**
```bat
start.bat
```

**Mac / Linux:**
```bash
bash start.sh
```

Then open **http://localhost:5173** in your browser.

> The script checks for venv, .env, and node_modules automatically and opens both servers.

---

## 🏭 Production Deployment

### Option A — Same Server (Recommended for small teams)

Run the FastAPI backend and serve the built React frontend as static files from nginx or the same server.

#### Step 1 — Build the frontend

```bash
# Set your real backend URL first
# Edit frontend/dashboard/.env.production:
#   VITE_API_BASE_URL=https://your-domain.com

cd frontend/dashboard
npm install
npm run build
# Output: frontend/dashboard/dist/
```

#### Step 2 — Set production environment variables

```bash
cp .env.example .env
# Edit .env with real values:
#   APP_ENV=production
#   ALLOWED_ORIGINS=https://your-domain.com
#   HUBSPOT_API_KEY=pat-na2-...
#   GMAIL_SENDER=...
#   Client_ID=...
#   Client_Secret=...
#   GMAIL_REFRESH_TOKEN=...
```

#### Step 3 — Start the backend (production mode)

```bash
# Windows
venv\Scripts\uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2

# Linux / Mac
venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2
```

#### Step 4 — Serve the frontend with nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Serve React static files
    root /path/to/CRM/frontend/dashboard/dist;
    index index.html;

    # SPA fallback — all routes go to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

#### Step 5 — Keep the backend alive with systemd (Linux)

```ini
# /etc/systemd/system/crm-api.service
[Unit]
Description=CRM Sequence Automator API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/path/to/CRM
ExecStart=/path/to/CRM/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
EnvironmentFile=/path/to/CRM/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable crm-api
sudo systemctl start crm-api
```

#### Step 6 — Keep the scheduler alive with systemd (Linux)

```ini
# /etc/systemd/system/crm-scheduler.service
[Unit]
Description=CRM Email Sequence Scheduler
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/path/to/CRM
ExecStart=/path/to/CRM/venv/bin/python backend/core/scheduler.py
Restart=always
EnvironmentFile=/path/to/CRM/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable crm-scheduler
sudo systemctl start crm-scheduler
```

---

### Option B — Windows (Task Scheduler + always-on)

1. **Backend:** Create a Task Scheduler task that runs on startup:
   - Action: `C:\path\to\CRM\venv\Scripts\uvicorn.exe backend.main:app --host 0.0.0.0 --port 8000 --workers 2`
   - Start in: `C:\path\to\CRM`

2. **Scheduler:** Create a second task:
   - Action: `C:\path\to\CRM\venv\Scripts\python.exe backend\core\scheduler.py`
   - Start in: `C:\path\to\CRM`
   - Trigger: At startup, repeat every 30 min

3. **Frontend:** Build once (`npm run build`) and serve `dist/` with IIS or nginx for Windows.

---

### Option C — Cloud (Railway / Render / Heroku)

A `Procfile` is included at the root:

```
web: venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 2
scheduler: venv/bin/python backend/core/scheduler.py
```

Set all environment variables from `.env.example` in your cloud provider's dashboard.
Build the frontend locally and commit `dist/` (or use a separate static hosting service like Vercel/Netlify for the frontend).

---

### Option D — Vercel (Frontend Only)

The frontend React app can be deployed to Vercel as a static site. A `vercel.json` is included at the root to handle SPA routing:

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

#### Steps to deploy frontend to Vercel:

1. **Install Vercel CLI** (if not already installed):
   ```bash
   npm install -g vercel
   ```

2. **Build the frontend:**
   ```bash
   cd frontend/dashboard
   npm install
   npm run build
   ```

3. **Set the API base URL** before building — edit `frontend/dashboard/.env.production`:
   ```env
   VITE_API_BASE_URL=https://your-backend-url.com
   ```

4. **Deploy to Vercel:**
   ```bash
   # From the CRM root folder
   vercel --prod
   ```
   Or connect your GitHub repo to [vercel.com](https://vercel.com) and it will auto-deploy on every push.

5. **Set environment variables** in Vercel dashboard → Project → Settings → Environment Variables:
   - `VITE_API_BASE_URL` = your backend URL (e.g. Railway/Render URL)

> ⚠️ Vercel only hosts the **frontend**. The Python backend (FastAPI + scheduler) must run on a separate server (Railway, Render, VPS, or your local machine).

---

### Production Checklist

| # | Item | Notes |
|---|------|-------|
| ☐ | `.env` has real credentials | Never commit `.env` |
| ☐ | `APP_ENV=production` | Disables `/docs`, enables JSON logging |
| ☐ | `ALLOWED_ORIGINS=https://your-domain.com` | Restricts CORS to your domain |
| ☐ | Frontend built with correct `VITE_API_BASE_URL` | Edit `.env.production` before `npm run build` |
| ☐ | Backend running with `--workers 2` | Not `--reload` in production |
| ☐ | Scheduler running as a separate process | Keeps emails firing every 30 min |
| ☐ | SPF / DKIM / DMARC configured | #1 reason emails land in spam |
| ☐ | Logs directory writable | `logs/scheduler.log` must be writable |
| ☐ | HTTPS configured | Required for production — use Let's Encrypt |

---

---

## Overview

Phase 3 sends a 4-email follow-up sequence (Day 1 → 3 → 7 → 14) via Gmail API,
all on the **same Gmail thread**, using the official HubSpot Python SDK for CRM state.
Scheduling is handled by APScheduler (or cron). No n8n. No HubSpot Sales Hub.

---

## File Structure

```
CRM/
├── .env                              # API keys and config (never commit this)
├── .gitignore                        # Git ignore rules
├── readme.md                         # This file
├── venv/                             # Python virtual environment (not committed)
│
├── backend/                          # All Python source code
│   ├── __init__.py
│   ├── requirements.txt              # Python dependencies
│   ├── main.py                       # FastAPI backend (dashboard API, port 8000)
│   │
│   ├── core/                         # 🔧 Core automation engine
│   │   ├── scheduler.py              # Entry point — APScheduler (run this to start)
│   │   ├── sequence_runner.py        # Orchestrator — ties all modules together
│   │   ├── email_templates.py        # Plain-text email copy (Day 1/3/7/14 + stalled)
│   │   ├── gmail_sender.py           # Gmail API sender (thread support)
│   │   ├── hubspot_crm.py            # HubSpot SDK — read/write contact state
│   │   └── email_throttle.py         # Business hours, warmup ramp, daily cap
│   │
│   ├── setup/                        # 🛠️ One-time setup & data import
│   │   ├── gmail_setup.py            # Gmail OAuth setup + connection test
│   │   ├── validate_csv.py           # Pre-import CSV validator
│   │   ├── import_contact.py         # CSV → HubSpot importer
│   │   └── setup_hubspot_properties.py  # Creates custom HubSpot properties
│   │
│   └── utils/                        # 🔍 Utilities & testing tools
│       ├── check_contact.py          # Look up a contact's HubSpot properties
│       ├── fix_thread_id.py          # Repair missing thread_id for a contact
│       ├── run_reply_check.py        # Manually trigger reply detection
│       ├── test_yopmail.py           # Send Day 1 to all yopmail test contacts
│       ├── test_reply_detection.py   # End-to-end reply detection test
│       └── debug_hubspot.py          # HubSpot API debug helper
│
├── frontend/
│   └── dashboard/                    # React + Vite dashboard (port 5173)
│       ├── index.html
│       ├── package.json
│       └── src/
│           ├── App.jsx               # Main app with auto-refresh
│           ├── api.js                # API client (fetch wrapper → localhost:8000)
│           └── components/
│               ├── Sidebar.jsx
│               ├── TopBar.jsx
│               ├── ThrottleBar.jsx
│               ├── KPICards.jsx
│               ├── ContactsTable.jsx
│               ├── QuickActions.jsx
│               ├── EngineStatus.jsx
│               └── LogTerminal.jsx
│
├── logs/                             # Auto-created on first run
│   ├── scheduler.log                 # All sequence activity
│   ├── import.log                    # CSV import history
│   ├── validation.log                # CSV validation results
│   └── throttle_state.json           # Daily send counter + warmup state
│
└── data/
    └── *.csv                         # Expo contact CSVs
```

---

## 📧 Quick Test — Send a Single Email to Yopmail Right Now

To immediately send a Day 1 test email to `test.cold.lead@yopmail.com` (bypassing the business-hours throttle window):

```bash
# Windows
venv\Scripts\python test_send_yopmail.py

# Mac/Linux
venv/bin/python test_send_yopmail.py
```

**What it does:**
1. Bypasses the business-hours throttle window
2. Sets `expo_followup_date = today` on the yopmail contact in HubSpot
3. Sends a Day 1 email via Gmail API to `test.cold.lead@yopmail.com`
4. Updates HubSpot contact status to `Contacted`

**Check the email at:** [https://yopmail.com/?test.cold.lead](https://yopmail.com/?test.cold.lead)

---

## 🧪 Test Mode — Run the Email Sequence (Fastest Way to Test)

The test sequence sends all 5 emails **15 minutes apart** (instead of Day 1/3/7/14) so you can verify the full flow in ~1 hour.

### Run for a single contact:
```bash
# Windows
venv\Scripts\python backend\utils\test_sequence.py --email test.bulk.new@yopmail.com

# Mac/Linux
venv/bin/python backend/utils/test_sequence.py --email test.bulk.new@yopmail.com
```

### Run for all yopmail test contacts:
```bash
venv\Scripts\python backend\utils\test_sequence.py --all
```

### What happens during the test:
| Step | What you'll see |
|---|---|
| Email 1 sent | Gmail ID logged, HubSpot engagement created, Lead Status → **Contacted** |
| 15 min wait | Checks for reply every 60 seconds |
| Email 2 sent | Lead Status → **Followed-up-1** |
| Email 3 sent | Lead Status → **Followed-up-2** |
| Email 4 sent | Lead Status → **Followed-up-3** |
| Email 5 sent | Lead Status → **Cold** (if no reply) |
| Reply detected | Sequence stops, Lead Status → **Replied**, Deal created in HubSpot |

### Stop anytime:
```
Ctrl+C
```

### Check the log:
```bash
# Windows
type logs\test_sequence.log

# Mac/Linux
cat logs/test_sequence.log
```

> 💡 Check [yopmail.com](https://yopmail.com) to see the emails arrive in the test inbox. Reply from yopmail to trigger reply detection.

---

## ⚡ Quick Start — How to Run This Project

### Step 1 — Clone or download the project
```bash
git clone <your-repo-url>
cd CRM
```

### Step 2 — Create the virtual environment
```bash
# Windows
python -m venv venv

# Mac/Linux
python3 -m venv venv
```

### Step 3 — Activate the virtual environment
```bash
# Windows (Command Prompt)
venv\Scripts\activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Mac/Linux
source venv/bin/activate
```

> ✅ You should see `(venv)` at the start of your terminal prompt.

### Step 4 — Install dependencies (inside venv)
```bash
pip install -r backend\requirements.txt
```

> ⚠️ Make sure the venv is **activated** before running this, so packages install into the venv and not globally.

### Step 5 — Configure your `.env` file
Copy the example and fill in your credentials:
```bash
# Edit .env with your actual values
```

| Variable | Description |
|---|---|
| `HUBSPOT_API_KEY` | HubSpot Private App token (pat-na2-...) |
| `GMAIL_SENDER` | Your Gmail address |
| `Client_ID` | Google OAuth client ID |
| `Client_Secret` | Google OAuth client secret |
| `GMAIL_REFRESH_TOKEN` | From OAuth Playground |
| `STALLED_DAYS` | Days of silence before re-engagement (default: 14) |
| `MAX_EMAILS_PER_DAY` | Hard ceiling on daily sends (default: 150) |
| `BUSINESS_HOURS_START` | Send window start hour, 24h (default: 9) |
| `BUSINESS_HOURS_END` | Send window end hour, 24h (default: 17) |
| `SENDER_TIMEZONE` | IANA timezone string (default: America/Chicago) |

### Step 6 — Test Gmail connection
```bash
# Windows
venv\Scripts\python backend\setup\gmail_setup.py

# Mac/Linux
venv/bin/python backend/setup/gmail_setup.py
```
Check your inbox for the test email.

### Step 7 — Check throttle status
```bash
# Windows
venv\Scripts\python backend\core\scheduler.py --status

# Mac/Linux
venv/bin/python backend/core/scheduler.py --status
```

### Step 8 — Run the sequence
```bash
# Single run (manual test)
venv\Scripts\python backend\core\scheduler.py --run-now

# Continuous mode (recommended for production — runs every 30 min)
venv\Scripts\python backend\core\scheduler.py
```

---

## 🔗 How to Add This App to Your HubSpot CRM

Follow these steps to connect this automation to your HubSpot account:

### Step 1 — Create a HubSpot Private App

1. Log in to [HubSpot](https://app.hubspot.com)
2. Go to **Settings** (gear icon, top right)
3. In the left sidebar, go to **Integrations → Private Apps**
4. Click **Create a private app**
5. Give it a name, e.g. `Email Sequence Automation`
6. Under **Scopes**, enable the following:
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`
   - `crm.schemas.contacts.read`
   - `crm.schemas.contacts.write`
7. Click **Create app** → Copy the **Access Token** (starts with `pat-na2-...`)
8. Paste it into your `.env` file as `HUBSPOT_API_KEY`

---

### Step 2 — Create Custom Contact Properties in HubSpot

Go to **HubSpot → Settings → Properties → Contact properties → Create property**.

Create **all** of the following (internal names must match exactly):

| Internal Name | Type | Label |
|---|---|---|
| `expo_followup_date` | Date | Expo Follow-up Date |
| `lead_type` | Single-line text | Lead Type |
| `expo_name` | Single-line text | Expo Name |
| `email_sequence_day` | Number | Email Sequence Day |
| `email_thread_id` | Single-line text | Email Thread ID |
| `email_last_message_id` | Single-line text | Email Last Message ID |
| `email_references` | Multi-line text | Email References |
| `email_replied` | Single checkbox | Email Replied |
| `email_replied_at` | Date and time | Email Replied At |
| `email_stalled_sent` | Single checkbox | Email Stalled Sent |
| `email_stalled_sent_at` | Date and time | Email Stalled Sent At |
| `email_sequence_complete` | Single checkbox | Email Sequence Complete |

> 💡 **Tip:** You can create properties in bulk via HubSpot's API or import them via Settings → Properties → Import.

---

### Step 3 — Import Contacts into HubSpot

1. Prepare your CSV file in the `data/` folder
2. Validate it first:
   ```bash
   venv\Scripts\python backend\setup\validate_csv.py data/your_contacts.csv
   ```
3. Import to HubSpot:
   ```bash
   venv\Scripts\python backend\setup\import_contact.py data/your_contacts.csv
   ```

Your CSV must include these columns:
- `email` — contact's email address
- `firstname` — first name
- `lastname` — last name
- `expo_followup_date` — date to start the sequence (YYYY-MM-DD)
- `lead_type` — e.g. `Bulk Liquid`, `Private Label`, `General`
- `expo_name` — name of the expo/event

---

### Step 4 — Set Up Gmail OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable the **Gmail API**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Application type: **Desktop app**
6. Download the credentials JSON
7. Go to [OAuth 2.0 Playground](https://developers.google.com/oauthlib/oauth2/playground)
   - Click ⚙️ Settings → check **Use your own OAuth credentials**
   - Enter your Client ID and Client Secret
   - In Step 1, select scope: `https://mail.google.com/`
   - Click **Authorize APIs** → **Exchange authorization code for tokens**
   - Copy the **Refresh token**
8. Add to `.env`:
   ```
   Client_ID=your-client-id
   Client_Secret=your-client-secret
   GMAIL_REFRESH_TOKEN=your-refresh-token
   GMAIL_SENDER=your@gmail.com
   ```

---

### Step 5 — Customize Email Templates

Open `email_templates.py` and update the constants at the top:
```python
SENDER_NAME = "Your Name"
COMPANY     = "Your Company Name"
WEBSITE     = "https://yourcompany.com"
```
Edit the email copy in each function to match your voice and product.

---

### Step 6 — Run the Automation

```bash
# Check everything is working
venv\Scripts\python backend\core\scheduler.py --status

# Fire one cycle manually (good for testing)
venv\Scripts\python backend\core\scheduler.py --run-now

# Start the continuous scheduler (production)
venv\Scripts\python backend\core\scheduler.py
```

---

## ✅ Pre-Launch Checklist (Do These in Order)

Work through each step before going live. Skipping any of these is the #1 reason cold outreach fails.

---

### ☐ 1 — Verify SPF / DKIM / DMARC on your sending domain

> ⚠️ **This is the #1 reason cold outreach lands in spam. Do not skip.**

Even warm follow-ups get filtered without proper DNS records. Check before sending a single email.

| Record | What to add |
|---|---|
| **SPF** | TXT record on your domain: `v=spf1 include:_spf.google.com ~all` |
| **DKIM** | Google Workspace Admin → Apps → Gmail → Authenticate email → Generate DKIM key → add TXT record to DNS |
| **DMARC** | TXT record at `_dmarc.yourdomain.com`: `v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com` |

**Verify with:**
- [https://www.mail-tester.com](https://www.mail-tester.com)
- [https://mxtoolbox.com/emailhealth](https://mxtoolbox.com/emailhealth)

Start DMARC with `p=none` (monitor only), then move to `p=quarantine` after 2 weeks of clean reports.

---

### ☐ 2 — Set up Gmail API credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com) → Create a new project
2. Enable the **Gmail API**
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
4. Application type: **Desktop app** → Download `credentials.json`
5. Run the auth flow once to generate `token.json`
6. Store both files securely on the server — **never commit to git** (already covered by `.gitignore`)

> 💡 Use a **dedicated sending Gmail account** (e.g. `outreach@yourdomain.com`), not the CEO's personal inbox. This keeps sending reputation separate and protects the main account.

---

### ☐ 3 — Install Python dependencies inside venv

```bash
# Create and activate venv
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Pin exact versions for reproducibility
pip freeze > requirements.txt
```

> ⚠️ Always install inside the venv — minor version mismatches can break Gmail API auth.

---

### ☐ 4 — Write and review all 4 email templates

Open `email_templates.py` and review/edit each template:

| Day | Purpose | Key rule |
|---|---|---|
| Day 1 | Intro + brochure link (not attachment — link to hosted PDF) | Keep under 100 words |
| Day 3 | Case study (e.g. Iraq container example) | No HTML, no images |
| Day 7 | Ask: Bulk Liquid or Private Label? | Look like a real person email |
| Day 14 | Last nudge | No unsubscribe link |

Use `{expo_name}`, `{first_name}`, `{lead_type}` as placeholders. Update constants at the top:
```python
SENDER_NAME = "Your Name"
COMPANY     = "Your Company Name"
WEBSITE     = "https://yourcompany.com"
```

> 💡 The goal is to look like a real email from a real person — not a marketing blast. No HTML, no images, no unsubscribe link.

---

### ☐ 5 — Verify Gmail threading is working

The send function (`gmail_sender.py`) handles threading automatically:

- **Day 1:** No `thread_id` → Gmail creates a new thread → `threadId` and `messageId` stored in HubSpot
- **Days 3/7/14:** Uses stored `threadId` + sets `In-Reply-To` header → Gmail appends to same thread

> ⚠️ Store `threadId` and `last_message_id` as custom HubSpot contact properties after every send. If you lose them, the next email starts a new thread instead of replying.

---

### ☐ 6 — Configure throttling and scheduling

Edit `.env` to set your limits:

```env
MAX_EMAILS_PER_DAY=100      # Start at 100 during warmup (first 2 weeks), then ramp to 300
BUSINESS_HOURS_START=9      # 9am sender timezone
BUSINESS_HOURS_END=17       # 5pm sender timezone
SENDER_TIMEZONE=America/Chicago
STALLED_DAYS=14             # Days before stalled re-engagement fires
```

**Throttle rules built in:**
- Max 100/day during warmup week 1 (days 1–7)
- Max 150/day during warmup week 2 (days 8–14)
- Max 300/day after warmup
- Sends randomized across business hours window (not all at 9:00am — that's a spam signal)
- Weekends skipped entirely

---

### ☐ 7 — Verify reply detection is working

The sequence runner checks for replies every cycle (every 30 min). For each active contact with a `threadId`, it:
1. Calls Gmail API `threads.get()` to check for new messages
2. Checks if any message is **FROM the lead** (not from your sending address)
3. If reply found → sets `email_replied = true` in HubSpot → stops all further sends

> ⚠️ Gmail threads include your own sent messages. Only flag as "replied" if the message is from the lead's email address, not your sending address.

---

### ☐ 8 — Verify stalled conversation detector is working

The stalled logic runs each cycle. It queries HubSpot for contacts where:
- `email_replied = true` AND
- Last reply date < (today − `STALLED_DAYS`)

For each stalled contact → sends a re-engagement message on the **same Gmail thread** → sets `email_stalled_sent = true` in HubSpot.

> 💡 `STALLED_DAYS` is configurable in `.env`. Default is 14 days — good for B2B sales.

---

### ☐ 9 — Test end-to-end with Yopmail test contacts

Before going live with real contacts, run a full end-to-end test:

1. Import the 7 yopmail test contacts with `expo_followup_date = tomorrow`
2. Run one cycle: `venv\Scripts\python backend\core\scheduler.py --run-now`
3. Check [yopmail.com](https://yopmail.com) inbox for Day 1 email
4. Reply from yopmail → wait up to 30 min → verify reply detection fires
5. Verify no Day 3 email sends after reply
6. Verify `Lead Status = Replied` in HubSpot contact record
7. Let a thread go stale → verify Stalled logic fires after `STALLED_DAYS`

> 💡 Test on a **Thursday** so Day 3 falls on Monday — same as real expo timing. Check the spam folder in yopmail. If Day 1 lands in spam, fix SPF/DKIM before going live with real contacts.

---

## Before You Go Live — SPF / DKIM / DMARC

**Do this before sending a single email.** Without these records, your emails
will land in spam or be rejected outright.

### SPF
Add a TXT record to your domain's DNS:
```
v=spf1 include:_spf.google.com ~all
```

### DKIM
In Google Workspace Admin → Apps → Gmail → Authenticate email → Generate DKIM key.
Add the generated TXT record to your DNS. Wait 24–48 hours for propagation.

### DMARC
Add a TXT record at `_dmarc.yourdomain.com`:
```
v=DMARC1; p=none; rua=mailto:dmarc-reports@yourdomain.com
```
Start with `p=none` (monitor only), then move to `p=quarantine` after 2 weeks.

### Verify
```bash
# Check SPF
nslookup -type=TXT yourdomain.com

# Send a test and check headers at
# https://www.mail-tester.com  or  https://mxtoolbox.com/emailhealth
```

---

## Running the Sequence

### Option A — APScheduler (recommended for always-on servers)
```bash
venv\Scripts\python backend\core\scheduler.py
```
Runs every 30 minutes. Fires once immediately on startup.
Keep this process alive with `screen`, `pm2`, or `systemd`.

### Option B — Single run (manual / cron)
```bash
venv\Scripts\python backend\core\scheduler.py --run-now
```

### Option C — Windows Task Scheduler
- Action: `C:\path\to\CRM\venv\Scripts\python.exe backend\core\scheduler.py --run-now`
- Trigger: Daily, repeat every 30 minutes, between 09:00 and 17:00

### Option D — Linux cron
```cron
# Every 30 min, Mon-Fri, 9am-5pm
*/30 9-16 * * 1-5 /path/to/CRM/venv/bin/python /path/to/CRM/backend/core/scheduler.py --run-now >> /path/to/CRM/logs/cron.log 2>&1

# Hourly outside hours (catches overnight replies)
0 * * * * /path/to/CRM/venv/bin/python /path/to/CRM/backend/core/scheduler.py --run-now >> /path/to/CRM/logs/cron.log 2>&1
```

### Check status
```bash
venv\Scripts\python backend\core\scheduler.py --status
```

---

## How the Sequence Works

```
expo_followup_date arrives
        │
        ▼
   Day 1 email sent ──────────────────────────────────────────────┐
   (new Gmail thread)                                             │
        │                                                         │
   2 days later                                              Contact replies?
        │                                                    YES → sequence stops
        ▼                                                    NO  → continue
   Day 3 reply (same thread)
        │
   4 days later
        │
        ▼
   Day 7 reply (same thread)
        │
   7 days later
        │
        ▼
   Day 14 reply (same thread) → contact archived in HubSpot

If contact replied and then went silent for STALLED_DAYS:
   → Stalled re-engagement sent on same thread
```

### Throttle rules
| Rule | Value |
|---|---|
| Business hours | 9 am – 5 pm (SENDER_TIMEZONE) |
| Weekends | Skipped entirely |
| Warmup week 1 (days 1–7) | Max 100 emails/day |
| Warmup week 2 (days 8–14) | Max 150 emails/day |
| Warmup week 3+ | Max 300 emails/day |
| Hard ceiling | MAX_EMAILS_PER_DAY from .env |
| Delay between sends | 45–180 seconds (randomised) |

---

## Logs

| File | Contents |
|---|---|
| `logs/scheduler.log` | All sequence activity, sends, replies, errors |
| `logs/throttle_state.json` | Daily counter + warmup start date |
| `logs/import.log` | Phase 2 import history |
| `logs/validation.log` | Phase 2 CSV validation results |

---

## Yopmail Test Contacts

| Email | Tests |
|---|---|
| test.bulk.new@yopmail.com | Day 1 fires for Bulk Liquid |
| test.private.new@yopmail.com | Day 1 fires for Private Label |
| test.general.new@yopmail.com | Day 1 fires for General |
| test.day3.check@yopmail.com | Day 3 follow-up |
| test.day7.check@yopmail.com | Day 7 follow-up |
| test.day14.check@yopmail.com | Day 14 last nudge |
| test.reply.check@yopmail.com | Reply stops sequence |
| test.stalled.check@yopmail.com | Stalled logic after STALLED_DAYS |
| test.cold.check@yopmail.com | Cold — no emails sent |
| test.archived.check@yopmail.com | Archived — no emails sent |

---

---

## 🖥️ UI Dashboard — React + FastAPI

A full-stack web dashboard to monitor and control the automation in real time.

### What it shows
| Section | Details |
|---|---|
| **Throttle Bar** | Capacity %, emails sent today vs daily cap, window open/closed |
| **KPI Cards** | Total contacts, active sequences, replied, stalled leads |
| **Contacts Table** | All HubSpot contacts with status badges, sequence day, last activity |
| **Quick Actions** | Trigger Run, Check Replies, Check Stalled — all call the backend API |
| **Engine Status** | HubSpot API connectivity, send window, daily quota progress |
| **Log Terminal** | Live view of `scheduler.log` — color-coded by INFO / WARN / ERROR |

Auto-refreshes every **30 seconds**. Shows a red banner if the backend is offline.

---

### File Structure

```
CRM/
├── backend/
│   ├── __init__.py
│   └── main.py          ← FastAPI app (port 8000)
└── frontend/
    └── dashboard/       ← React + Vite app (port 5173)
        ├── index.html   ← Tailwind CDN + design tokens
        ├── package.json
        └── src/
            ├── App.jsx              ← Main app with auto-refresh
            ├── api.js               ← API client (fetch wrapper)
            └── components/
                ├── Sidebar.jsx      ← Navigation sidebar
                ├── TopBar.jsx       ← Header with engine status
                ├── ThrottleBar.jsx  ← Email throughput bar
                ├── KPICards.jsx     ← 4 stat cards
                ├── ContactsTable.jsx← HubSpot contacts table
                ├── QuickActions.jsx ← Action buttons
                ├── EngineStatus.jsx ← System health panel
                └── LogTerminal.jsx  ← Live log viewer
```

---

### How to Run the Dashboard

#### Terminal 1 — Start the FastAPI Backend

```bash
# From the CRM root folder
cd c:\Users\abc\Downloads\CRM\CRM

# Windows
venv\Scripts\uvicorn backend.main:app --reload --port 8000

# Mac/Linux
venv/bin/uvicorn backend.main:app --reload --port 8000
```

Backend runs at: **http://localhost:8000**
API docs (auto-generated): **http://localhost:8000/docs**

#### Terminal 2 — Start the React Frontend

```bash
# From the frontend/dashboard folder
cd c:\Users\abc\Downloads\CRM\CRM\frontend\dashboard

npm install      # first time only
npm run dev
```

Frontend runs at: **http://localhost:5173**

> Open **http://localhost:5173** in your browser to see the dashboard.

---

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Backend health check |
| GET | `/api/dashboard` | KPI stats + throttle status |
| GET | `/api/contacts` | All contacts with sequence status |
| GET | `/api/throttle` | Current throttle/send window state |
| GET | `/api/logs?lines=50` | Last N lines from scheduler.log |
| POST | `/api/run-now` | Trigger a full sequence run |
| POST | `/api/check-replies` | Run reply detection only |
| POST | `/api/check-stalled` | Run stalled check only |

---

### Quick Start (Both Servers)

Open **two terminal windows** and run:

```bash
# Terminal 1 — Backend
cd c:\Users\abc\Downloads\CRM\CRM
venv\Scripts\uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd c:\Users\abc\Downloads\CRM\CRM\frontend\dashboard
npm run dev
```

Then open **http://localhost:5173** in your browser.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Make sure venv is activated and `pip install -r requirements.txt` was run inside it |
| `HUBSPOT_API_KEY not set` | Check your `.env` file has the correct token |
| `Gmail auth error` | Re-run `gmail_setup.py` to refresh OAuth token |
| Emails going to spam | Set up SPF/DKIM/DMARC records on your domain |
| `No contacts to process` | Check HubSpot contacts have `expo_followup_date` set and `email_sequence_day` is 0 or empty |
| **"You have reached a limit for sending mail"** | Gmail daily sending limit hit — see below |
| `email_sequence_day update failed: Bad Request` | Custom property not created yet — run `setup_hubspot_properties.py` (requires `crm.schemas.contacts.write` scope on your HubSpot token) |

---

## ⚠️ Gmail Sending Limits

If you see **"You have reached a limit for sending mail. Your message was not sent."** from `mailer-daemon@googlemail.com`, your Gmail account has hit its daily sending quota.

### Gmail API Daily Limits

| Account Type | Daily Limit |
|---|---|
| Free Gmail (`@gmail.com`) | **500 emails/day** |
| Google Workspace (paid) | **2,000 emails/day** |

### What to do

1. **Wait until midnight** — the quota resets at midnight Pacific Time (Google's servers)
2. **Reduce `MAX_EMAILS_PER_DAY`** in your `.env` to stay under the limit:
   ```env
   MAX_EMAILS_PER_DAY=50   # Safe for free Gmail during testing
   ```
3. **For production** — upgrade to Google Workspace (`$6/month`) to get the 2,000/day limit
4. **For high volume** — use a dedicated sending service (SendGrid, Mailgun, AWS SES) instead of Gmail API

### During testing

The test sequence sends multiple emails per contact. If you're testing with many contacts, you can hit the limit quickly. Use a **single test contact** at a time:

```bash
# Test with just one contact (5 emails total)
venv\Scripts\python backend\utils\test_sequence.py --email test.bulk.new@yopmail.com
```

> 💡 The quota resets at midnight. If you hit the limit, just wait until tomorrow and run again.
