# Personal Finance Tracker - Project Planning & Architecture

## 1. Project Overview
An AI-powered personal finance tracker tailored specifically for students and young adults. The system helps users track daily expenses, manage budgets across categories, monitor savings goals, receive automated analytical insights, and leverage an AI recommendation engine to optimize spending habits and reach financial milestones.

---

## 2. System Architecture

```
personal-finance-tracker/
│
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint, middleware, routers registration
│   │   ├── database/         # SQLite connection & SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic data validation schemas
│   │   ├── routers/          # API route handlers
│   │   ├── services/         # Business logic layer
│   │   ├── ai/               # AI recommendation and budgeting engine
│   │   └── utils/            # Helper utilities and formatters
│   ├── requirements.txt      # Backend dependencies
│   └── finance.db            # SQLite database file
│
├── frontend/                 # User Interface (React / Web dashboard)
│
├── tests/                    # Backend automated tests (pytest)
│   ├── test_onboarding.py
│   ├── test_expenses.py
│   ├── test_budget.py
│   └── test_analytics.py
│
├── planning.md               # Architecture, schema, and API specifications
├── README.md                 # Setup and usage guide
└── .gitignore
```

---

## 3. Database Schema Design (SQLAlchemy / SQLite)

### 3.1 Student / User
- `id` (Integer, Primary Key)
- `name` (String)
- `email` (String, Unique)
- `monthly_allowance` (Float)
- `currency` (String, default="USD")
- `college_year` (String, optional)
- `created_at` (DateTime)

### 3.2 Expense
- `id` (Integer, Primary Key)
- `student_id` (Integer, Foreign Key)
- `title` (String)
- `amount` (Float)
- `category` (String: Food, Books, Rent, Entertainment, Travel, Utilities, Others)
- `date` (Date)
- `payment_method` (String: UPI, Card, Cash, etc.)
- `notes` (String, optional)
- `created_at` (DateTime)

### 3.3 Budget
- `id` (Integer, Primary Key)
- `student_id` (Integer, Foreign Key)
- `category` (String)
- `monthly_limit` (Float)
- `month` (Integer: 1-12)
- `year` (Integer)
- `created_at` (DateTime)

### 3.4 Goal (Savings Goals)
- `id` (Integer, Primary Key)
- `student_id` (Integer, Foreign Key)
- `title` (String)
- `target_amount` (Float)
- `current_amount` (Float, default=0.0)
- `deadline` (Date)
- `status` (String: In Progress, Achieved, Abandoned)
- `created_at` (DateTime)

### 3.5 Recommendation
- `id` (Integer, Primary Key)
- `student_id` (Integer, Foreign Key)
- `title` (String)
- `message` (Text)
- `category` (String)
- `impact_level` (String: Low, Medium, High)
- `is_read` (Boolean, default=False)
- `created_at` (DateTime)

---

## 4. API Endpoints Specification

### 4.1 Onboarding & Profile (`/api/onboarding`)
- `POST /api/onboarding/register` - Register a new student profile
- `GET /api/onboarding/profile/{student_id}` - Retrieve student profile
- `PUT /api/onboarding/profile/{student_id}` - Update monthly allowance or details

### 4.2 Expenses (`/api/expenses`)
- `POST /api/expenses/` - Log a new expense
- `GET /api/expenses/{student_id}` - List expenses with filtering (category, date range)
- `DELETE /api/expenses/{expense_id}` - Delete an expense entry
- `GET /api/expenses/{expense_id}/summary` - Get expense summary

### 4.3 Budgets (`/api/budgets`)
- `POST /api/budgets/` - Set or update budget limit for a category
- `GET /api/budgets/{student_id}` - Fetch active budgets and current spending vs limit
- `GET /api/budgets/{student_id}/alerts` - Check for exceeded or near-limit budgets

### 4.4 Goals (`/api/goals`)
- `POST /api/goals/` - Create a savings target
- `GET /api/goals/{student_id}` - Get list of goals and progress percentages
- `PATCH /api/goals/{goal_id}/deposit` - Add savings towards a goal

### 4.5 Analytics (`/api/analytics`)
- `GET /api/analytics/{student_id}/overview` - Total spent, remaining allowance, savings rate
- `GET /api/analytics/{student_id}/by-category` - Category-wise spending breakdown
- `GET /api/analytics/{student_id}/trends` - Daily and weekly expenditure trends

### 4.6 Recommendations & AI Engine (`/api/recommendations`)
- `GET /api/recommendations/{student_id}` - Get actionable AI-generated advice
- `POST /api/recommendations/{student_id}/generate` - Trigger recommendation engine evaluation
- `GET /api/recommendations/{student_id}/forecast` - Predict end-of-month balance and savings trajectory

---

## 5. Technology Stack
- **Backend**: FastAPI (Python 3.10+), SQLAlchemy 2.0, Pydantic v2, Uvicorn
- **Database**: SQLite (`finance.db`)
- **Testing**: pytest, httpx (TestClient)
- **Frontend**: Modern Responsive Web Dashboard (HTML5, Vanilla CSS / React)
