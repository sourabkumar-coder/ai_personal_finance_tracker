# AI Personal Finance Tracker 💰🎓

A modern, student-centric personal finance tracking application equipped with budget monitoring, savings targets, financial analytics, and an AI recommendation engine to promote smart financial habits.

---

## 📁 Project Structure

```
personal-finance-tracker/
│
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application entrypoint
│   │   │
│   │   ├── database/
│   │   │   ├── database.py             # SQLite connection & session management
│   │   │   └── models.py               # SQLAlchemy ORM models
│   │   │
│   │   ├── schemas/
│   │   │   ├── student.py              # Pydantic schemas for student profile
│   │   │   ├── expense.py              # Schemas for expense entries
│   │   │   ├── budget.py               # Schemas for category budgets
│   │   │   ├── goal.py                 # Schemas for savings goals
│   │   │   └── recommendation.py       # Schemas for recommendations
│   │   │
│   │   ├── routers/
│   │   │   ├── onboarding.py           # Student signup & profile setup
│   │   │   ├── expenses.py             # Expense management endpoints
│   │   │   ├── budgets.py              # Budget limits & status endpoints
│   │   │   ├── goals.py                # Savings goals endpoints
│   │   │   ├── analytics.py            # Financial analytics & charts data
│   │   │   └── recommendations.py      # AI suggestions & forecasting
│   │   │
│   │   ├── services/
│   │   │   ├── budget_service.py       # Budget computation logic
│   │   │   ├── analytics_service.py    # Spending insights & metrics
│   │   │   ├── recommendation_service.py# Recommendation workflow
│   │   │   └── prediction_service.py   # Spending forecasting logic
│   │   │
│   │   ├── ai/
│   │   │   └── recommendation_engine.py# AI rule & pattern heuristics
│   │   │
│   │   └── utils/
│   │       └── helpers.py              # Calculation & date helpers
│   │
│   ├── requirements.txt                # Python backend dependencies
│   └── finance.db                      # Local SQLite database
│
├── frontend/                           # Web user interface
│
├── tests/
│   ├── test_onboarding.py              # Onboarding test suite
│   ├── test_expenses.py                # Expense management test suite
│   ├── test_budget.py                  # Budget test suite
│   └── test_analytics.py               # Analytics & reporting test suite
│
├── planning.md                         # Technical architecture & specs
├── README.md                           # Project documentation
└── .gitignore                          # Git ignore rules
```

---

## 🚀 Quickstart Guide

### 1. Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1

   # Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the FastAPI server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Interactive API Documentation:**
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

---

### 2. Running Tests

Run the test suite using `pytest`:
```bash
pytest
```

---

## 🛠️ Features
- **Student Onboarding**: Set monthly pocket money / stipend and personalized financial goals.
- **Smart Expense Logging**: Categorized tracking with instant payment method attribution.
- **Dynamic Budgets**: Category limits with auto-alerts when nearing 80% or 100% threshold.
- **Savings Target Milestones**: Set deadlines and track deposits incrementally.
- **Visual Analytics**: Real-time spending breakdown and day-by-day expenditure velocity.
- **AI Recommendation Engine**: Uncovers irregular spikes, identifies subscription leaks, and recommends achievable savings.
