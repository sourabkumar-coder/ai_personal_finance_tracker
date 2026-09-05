# AI Personal Finance Tracker with Automatic UPI/Bank Detection 💰⚡🎓

An intelligent, student-centric personal finance tracker that eliminates manual expense entry through **Zero-Friction UPI & Bank Transaction Detection**, **3-Tier AI Categorization**, real-time budget tracking, savings goal management, and Gemini-powered financial recommendations.

---

## 🌟 The Problem & The Solution

### ❌ The Friction of Manual Expense Tracking
For college students and young adults in India, UPI is the primary method of payment:
> Make UPI payment → Open finance app → Enter amount → Select category → Save entry

Because students make multiple micro-transactions daily (chai, snacks, metro, xerox), manual entry quickly leads to tracking fatigue, skipped entries, and abandoned budgets.

### ⚡ The Zero-Friction Experience
> Make UPI payment → Notification arrives on Android device → NotificationListener intercepts it locally → Deduplication & Safety filters run → 3-Tier AI categorizes merchant → Transaction automatically recorded → Web Dashboard updates in real time with toast alerts!

---

## 🏗️ Architecture & System Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                        ANDROID COMPANION LAYER                         │
│                                                                        │
│   Google Pay / PhonePe / Paytm / BHIM / HDFC / SBI / ICICI / Kotak     │
│                                  │                                     │
│                     [StatusBar Notification]                           │
│                                  ▼                                     │
│               TransactionNotificationListener (Service)                │
│                                  │                                     │
│            ┌─────────────────────┴──────────────────────┐              │
│            ▼                                            ▼              │
│   Safety & Privacy Filters                   Local TransactionParser   │
│   - Ignore OTP / PINs                        - Extract Amount (₹)      │
│   - Ignore Balance Inquiries                 - Extract Merchant        │
│   - Ignore Spam / Cashbacks                  - Detect EXPENSE vs INCOME│
│   - Reject Failed / Declined Txns            - Extract UPI Ref / UTR   │
│                                  │                                     │
│                     [Offline Queue Buffer (Fallback)]                  │
│                                  │                                     │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   │ HTTP POST /api/transactions/auto-detect
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND LAYER                          │
│                                                                        │
│                       Deduplication Service                            │
│                       - SHA-256 Fingerprint                            │
│                       - 15-Minute Sliding Window Check                 │
│                                  │                                     │
│                    3-Tier AI Categorizer Engine                        │
│   Tier 1: Student Category Preference Override (Confidence: 1.0)       │
│   Tier 2: Heuristics Dictionary (150+ Indian Merchants, Conf: 0.95)   │
│   Tier 3: Google Gemini 2.5 Flash API (Contextual Fallback)            │
│                                  │                                     │
│                   SQLAlchemy ORM & Local SQLite DB                     │
│                   - Stores expense with auto-detect metadata           │
│                   - Updates category preferences upon confirmation     │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   │
                     HTTP GET Polling (Every 4s)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          WEB DASHBOARD LAYER                           │
│                                                                        │
│   - 🟢 Live Auto-Tracking Status Banner with pulse dot                 │
│   - ⚡ Real-Time Toast Alerts on newly intercepted transactions        │
│   - Visual Badges: "⚡ Auto • PhonePe", "⚡ Auto • Google Pay"          │
│   - Inline Category Confirmation & Personalized AI Re-learning         │
│   - Interactive Notification Simulator for instant live demonstrations │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ai_personal_finance_tracker/
│
├── android/                                    # Native Android Companion App
│   ├── app/
│   │   ├── build.gradle.kts                    # App dependencies (Retrofit, Material 3, Coroutines)
│   │   ├── proguard-rules.pro                  # ProGuard rules
│   │   └── src/main/
│   │       ├── AndroidManifest.xml             # NotificationListenerService & Permissions
│   │       ├── java/com/smartfinance/tracker/
│   │       │   ├── MainActivity.kt             # Companion dashboard & status check
│   │       │   ├── model/Models.kt             # Requests, responses & parsed DTOs
│   │       │   ├── network/                    # Retrofit ApiClient & ApiService
│   │       │   ├── parser/TransactionParser.kt # On-device regex extraction engine
│   │       │   ├── service/                    # TransactionNotificationListener
│   │       │   ├── storage/                    # AppPreferences & OfflineTransactionQueue
│   │       │   └── ui/OnboardingActivity.kt    # Transparent privacy & permission explainer
│   │       └── res/                            # Layouts, values, themes & vector drawables
│   ├── build.gradle.kts                        # Root build configuration
│   ├── gradle.properties                       # AndroidX & JVM settings
│   └── settings.gradle.kts                     # Project settings
│
├── backend/
│   ├── app/
│   │   ├── main.py                             # FastAPI entrypoint
│   │   ├── ai/
│   │   │   ├── recommendation_engine.py        # Budget & savings heuristics
│   │   │   ├── transaction_categorizer.py      # 3-Tier AI categorizer (Gemini Flash)
│   │   │   └── transaction_parser.py           # Server-side regex extraction
│   │   ├── database/
│   │   │   ├── database.py                     # SQLAlchemy session manager
│   │   │   └── models.py                       # Student, Expense, CategoryPreference models
│   │   ├── routers/
│   │   │   ├── analytics.py                    # Financial analytics & velocity
│   │   │   ├── budgets.py                      # Budget limits & status
│   │   │   ├── expenses.py                     # Expense CRUD
│   │   │   ├── goals.py                        # Savings goals
│   │   │   ├── onboarding.py                   # Student profile setup
│   │   │   ├── recommendations.py              # AI recommendations & forecasting
│   │   │   └── transactions.py                 # Auto-detect, simulator & sync endpoints
│   │   ├── schemas/                            # Pydantic validation schemas
│   │   ├── services/
│   │   │   ├── analytics_service.py            # Aggregate insights
│   │   │   ├── budget_service.py               # Threshold calculations
│   │   │   ├── deduplication_service.py        # SHA-256 fingerprint & sliding window
│   │   │   ├── prediction_service.py           # Spending forecasts
│   │   │   └── recommendation_service.py       # Recommendation workflow
│   │   └── utils/helpers.py                    # Date & currency formatting
│   ├── requirements.txt                        # Python backend dependencies
│   └── .env                                    # Environment config (GEMINI_API_KEY)
│
├── frontend/                                   # Web Dashboard (Primary Interface)
│   ├── index.html                              # Dashboard, auto-tracking banner & simulator modal
│   ├── style.css                               # Glassmorphism, animations & dark UI theme
│   └── app.js                                  # 4s polling engine, toast alerts, API client
│
├── tests/
│   ├── test_analytics.py                       # Analytics test suite
│   ├── test_auto_detection.py                  # Auto-detection, parsing, deduplication tests
│   ├── test_budget.py                          # Budget test suite
│   ├── test_expenses.py                        # Expense CRUD test suite
│   ├── test_onboarding.py                      # Student onboarding test suite
│   └── test_recommendations.py                 # Recommendations test suite
│
├── pytest.ini                                  # Pytest configuration
└── README.md                                   # Comprehensive documentation
```

---

## ⚡ Core Features & Capabilities

### 1. 3-Tier AI Categorization Engine
Every detected transaction is categorized using a fail-safe, hierarchical intelligence pipeline:
1. **Tier 1: Personalized Student Preference** (Confidence: `1.0`)
   - Checks if the user previously confirmed or re-categorized a merchant (e.g., if a student changes *Amazon* from *Shopping* to *Education*, future Amazon transactions inherit *Education* automatically).
2. **Tier 2: Student Merchant Heuristic Dictionary** (Confidence: `0.95`)
   - 150+ high-frequency Indian student brands and merchants pre-mapped (Swiggy, Zomato, Zepto, Blinkit, Chai Point, IRCTC, Uber, Ola, Rapido, Campus Canteen, Xerox, Netflix, Spotify, Amazon, Flipkart, etc.).
3. **Tier 3: Google Gemini 2.5 Flash Fallback** (Confidence: `0.80 - 0.90`)
   - For unmapped merchants (e.g., local VPAs like `sharma_provisions@okaxis`), calls Gemini 2.5 Flash to deduce category based on name keywords and transaction context.

### 2. Strict Deduplication & Double-Count Prevention
- **SHA-256 Unique Fingerprinting**: Derived from UPI Reference ID (UTR) or a composite key of `(student_id, amount, merchant, date)`.
- **15-Minute Sliding Time Window**: Prevents duplicate bank SMS + UPI app push notifications from logging the same expense twice.
- **Failed & Cancelled Payment Rejection**: Rejects notifications containing "failed", "declined", "cancelled", or "unsuccessful".

### 3. Student Privacy & Security by Design
- **Zero SMS or WhatsApp Snooping**: Does not request or use `READ_SMS` permission.
- **Scoped Notification Access**: Only inspects notifications matching whitelisted UPI and banking app package IDs.
- **Strict Blacklist Filters**: Automatically drops OTPs, PIN alerts, available balance inquiries, and marketing spam before processing.

### 4. Real-Time Web Dashboard Sync
- Web dashboard polls every 4 seconds for newly detected transactions.
- Newly auto-detected items display dynamic source badges (`⚡ Auto • Google Pay`, `⚡ Auto • PhonePe`).
- Instant slide-in toast notifications inform the user the moment a payment is captured.
- Inline category confirmation allows students to tune the AI model with one click.

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+
- Modern Web Browser (Chrome, Safari, Firefox, Edge)
- (Optional) Android Studio Hedgehog+ or physical Android device (Android 8.0 / API 26+)

---

### Step 1: Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate

   # Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Open .env and insert your GEMINI_API_KEY (optional, fallback heuristics work offline)
   ```

5. **Start the FastAPI server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Verify API Docs:**
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Step 2: Open Web Dashboard

Simply open `frontend/index.html` in your web browser, or serve it using Python's built-in HTTP server:
```bash
# In project root:
python3 -m http.server 3000
```
Visit [http://localhost:3000/frontend/](http://localhost:3000/frontend/) in your browser.

---

### Step 3: Run Automated Tests

Execute the complete test suite (33 tests covering onboarding, expenses, budgets, analytics, recommendations, auto-detection, deduplication, and personalized AI learning):
```bash
python3 -m pytest -v
```

---

### Step 4: Android Companion App Setup

1. Open the `android/` directory in **Android Studio**.
2. Sync Gradle dependencies (`Sync Project with Gradle Files`).
3. Run the app on an Android Emulator or physical phone.
4. On first launch:
   - Tap **"Grant Notification Access"** and enable **SmartFinance UPI Notification Listener** in Android System Settings.
   - Tap the settings cog icon in the top right to verify the backend URL:
     - **For Android Emulator**: `http://10.0.2.2:8000/`
     - **For Physical Phone**: `http://<YOUR_COMPUTER_LOCAL_IP>:8000/` (e.g. `http://192.168.1.15:8000/`)
5. Make real UPI payments via Google Pay / PhonePe / Paytm, or tap **"Simulate Test Payment"** inside the app.

---

## 🧪 Live Demo & Hackathon Script

You can demonstrate the entire auto-detection pipeline **without needing a physical phone** using the built-in Web Notification Simulator:

1. Open the Web Dashboard at [http://localhost:3000/frontend/](http://localhost:3000/frontend/).
2. On the top overview banner, tap the **"⚡ Simulate Notification"** button (or press the **⚡ Auto-Tracking** tab in the sidebar).
3. Select a pre-configured quick sample:
   - **Sample 1: Zomato Order (Expense)**
     - Text: `Paid ₹420 to Zomato using UPI Ref: 482910394810`
     - *Result*: Automatically categorized as `Food & Dining` (Confidence: 95%). Green toast notification pops up. Dashboard balance and charts update immediately.
   - **Sample 2: Amazon Books (Personalized Learning Demo)**
     - Text: `Paid ₹1,200 to Amazon Pay India on 04-Sep-2026 Ref: 991823019284`
     - *Result*: Initially categorizes as `Shopping`.
     - In the Expense History table, click **Edit Category** and change it to `Education`.
     - Send the Amazon notification again: the system recognizes the user preference and categorizes it as `Education` with **100% confidence**!
   - **Sample 3: Pocket Money / Refund (Income)**
     - Text: `₹2,500 received from Papa UPI Ref: 382910293847`
     - *Result*: Detected as `INCOME`. Pocket money / balance increased without adding expense.
   - **Sample 4: Failed Payment (Safety Filter)**
     - Text: `Payment of ₹350 to Starbucks failed due to bank server issue`
     - *Result*: Rejected immediately. No false expense is logged.
   - **Sample 5: Bank Balance Query / OTP (Privacy Filter)**
     - Text: `Your available account balance in A/C XX1234 is ₹4,250.00`
     - *Result*: Dropped by filter. Balance queries and OTPs are never stored.

---

## 📡 API Reference

### `POST /api/transactions/auto-detect`
Ingests an auto-detected payment notification from Android companion app or web client.
- **Request Body:**
  ```json
  {
    "student_id": 1,
    "notification_text": "Paid ₹340 to Swiggy using UPI Ref: 392019283019",
    "source_app": "PhonePe"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "message": "Transaction auto-detected and logged successfully.",
    "action": "RECORDED",
    "expense_id": 14,
    "merchant": "Swiggy",
    "amount": 340.0,
    "category": "Food & Dining",
    "transaction_type": "EXPENSE",
    "confidence": 0.95,
    "is_duplicate": false,
    "detected_at": "2026-09-04T13:30:00"
  }
  ```

### `POST /api/transactions/simulate-notification`
Quick test endpoint to simulate incoming notifications for demos.

### `PATCH /api/transactions/{expense_id}/confirm`
Confirms or corrects an auto-detected expense's category and trains student-specific preferences.
- **Request Body:**
  ```json
  {
    "category": "Education"
  }
  ```

### `GET /api/transactions/{student_id}/status`
Returns real-time auto-tracking status, total auto-detected counts, and recent auto-detected transactions.

### `GET / PUT /api/transactions/{student_id}/settings`
Fetches or updates student auto-tracking preferences (toggle auto-detection, auto-budget alert push notifications, etc.).

---

## 🔒 Security & Privacy Commitments
1. **Zero Access to Personal Chats**: The companion app has no permissions to read SMS, WhatsApp, contacts, camera, or file storage.
2. **Local Regex Extraction**: Notifications are filtered on-device first before any network payload is constructed.
3. **Transparent Permission Model**: Uses standard Android `NotificationListenerService` which requires explicit user consent in Android system settings.
4. **Offline Resilience**: Offline queue stores transactions safely in encrypted SharedPreferences until internet is restored.

---

## 🏆 Summary of Hackathon Value
| Before | After (With Auto-Detection) |
|---|---|
| Manual entry of amount, merchant, date & category | **Zero manual entry required** |
| Requires opening app after every chai / snack | **Passive background detection** |
| Frequent forgotten expenses & inaccurate budgets | **100% complete expense history** |
| Generic static categories | **3-Tier AI with personalized self-learning** |
