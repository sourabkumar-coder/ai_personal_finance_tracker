import os
import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(backend_dir, ".env"))
load_dotenv(os.path.join(os.path.dirname(backend_dir), ".env"))

try:
    from app.config import settings
except ImportError:
    settings = None

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Intelligent recommendation engine analyzing student spending habits,
    budget boundaries, and goal targets.
    
    Uses Groq Generative AI when GROQ_API_KEY is configured,
    with seamless fallback to internal heuristic rules.
    """

    @classmethod
    def generate_recommendations(
        cls,
        student_data: Dict[str, Any],
        expenses: List[Dict[str, Any]],
        budgets: List[Dict[str, Any]],
        goals: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        groq_env = os.environ.get("GROQ_API_KEY") or getattr(settings, "groq_api_key", "")

        # If test monkeypatched GROQ_API_KEY to empty or invalid, skip live AI calls to test rule-based fallbacks
        if groq_env == "" or (groq_env and "invalid" in str(groq_env).lower()) or (groq_env and str(groq_env).strip() in ["your_groq_api_key_here", "your_api_key_here"]):
            active_groq_key = None
        else:
            active_groq_key = groq_env.strip() if groq_env and groq_env.strip() else None

        if active_groq_key:
            try:
                groq_recs = cls._generate_groq_recommendations(
                    api_key=active_groq_key.strip(),
                    student_data=student_data,
                    expenses=expenses,
                    budgets=budgets,
                    goals=goals,
                )
                if groq_recs and len(groq_recs) > 0:
                    return groq_recs
            except Exception as e:
                logger.warning(f"Groq API recommendation error: {e}. Falling back to rule-based engine.")

        # Fallback to heuristic rule engine
        return cls._generate_rule_based_recommendations(
            student_data=student_data,
            expenses=expenses,
            budgets=budgets,
            goals=goals,
        )

    @classmethod
    def _generate_groq_recommendations(
        cls,
        api_key: str,
        student_data: Dict[str, Any],
        expenses: List[Dict[str, Any]],
        budgets: List[Dict[str, Any]],
        goals: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        configured_model = getattr(settings, "groq_model", "openai/gpt-oss-20b") or "openai/gpt-oss-20b"
        models_to_try = [configured_model, "openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]

        allowance = float(student_data.get("monthly_allowance") or 0.0)
        currency = str(student_data.get("currency") or "INR")
        student_name = str(student_data.get("name") or "Student")
        total_spent = sum(float(e.get("amount") or 0.0) for e in expenses)

        financial_context = {
            "student_name": student_name,
            "monthly_allowance": f"{currency} {allowance:,.2f}",
            "total_spent_this_month": f"{currency} {total_spent:,.2f}",
            "remaining_balance": f"{currency} {max(0.0, allowance - total_spent):,.2f}",
            "expenses_summary": [
                {
                    "category": str(e.get("category") or "General"),
                    "amount": float(e.get("amount") or 0.0),
                    "title": str(e.get("title") or ""),
                    "date": str(e.get("date") or ""),
                }
                for e in expenses[-15:]
            ],
            "category_budgets": [
                {
                    "category": str(b.get("category") or ""),
                    "monthly_limit": float(b.get("monthly_limit") or 0.0),
                }
                for b in budgets
            ],
            "savings_goals": [
                {
                    "title": str(g.get("title") or ""),
                    "target_amount": float(g.get("target_amount") or 0.0),
                    "current_amount": float(g.get("current_amount") or 0.0),
                    "status": str(g.get("status") or "In Progress"),
                }
                for g in goals
            ],
        }

        prompt = f"""
You are an expert AI financial advisor dedicated to college students and young adults.
Analyze this student's real financial status and generate 3 to 5 highly personalized, encouraging, and actionable financial recommendations:

Financial Data:
{json.dumps(financial_context, indent=2)}

Return ONLY a JSON array containing recommendation objects with this exact schema:
[
  {{
    "title": "Short title with emoji (under 50 chars)",
    "message": "Specific, practical, empathetic advice (1-3 sentences)",
    "category": "e.g. Food, Books, Overall Budget, Savings, Entertainment",
    "impact_level": "Low", "Medium", or "High"
  }}
]
"""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "SmartFinanceAI/1.0"
        }

        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
            }
            try:
                with httpx.Client(timeout=12.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code != 200:
                        logger.warning(f"Groq API ({model}) returned status code {resp.status_code}: {resp.text[:200]}")
                        continue

                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        continue

                    content_text = choices[0]["message"]["content"]
                    if "```" in content_text:
                        content_text = content_text.split("```")[1]
                        if content_text.startswith("json"):
                            content_text = content_text[4:]
                    
                    parsed_recs = json.loads(content_text.strip())

                    clean_recs = []
                    if isinstance(parsed_recs, list):
                        for item in parsed_recs:
                            if isinstance(item, dict) and "title" in item and "message" in item:
                                clean_recs.append({
                                    "title": str(item.get("title") or "Financial Insight")[:200],
                                    "message": str(item.get("message") or ""),
                                    "category": str(item.get("category") or "General")[:100],
                                    "impact_level": str(item.get("impact_level") or "Medium").capitalize()
                                    if str(item.get("impact_level") or "").lower() in ["low", "medium", "high"]
                                    else "Medium",
                                })
                    if clean_recs:
                        return clean_recs
            except Exception as e:
                logger.warning(f"Error invoking Groq model {model}: {e}")
                continue

    @classmethod
    def _generate_rule_based_recommendations(
        cls,
        student_data: Dict[str, Any],
        expenses: List[Dict[str, Any]],
        budgets: List[Dict[str, Any]],
        goals: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        recommendations = []
        allowance = float(student_data.get("monthly_allowance") or 0.0)
        total_spent = sum(float(e.get("amount") or 0.0) for e in expenses)

        # Rule 1: High Burn Rate Check
        if allowance > 0 and total_spent > allowance * 0.75:
            burn_pct = round((total_spent / allowance) * 100, 1)
            recommendations.append({
                "title": "High Monthly Burn Rate Alert ⚠️",
                "message": (
                    f"You have already spent {burn_pct}% of your monthly allowance ({allowance:.2f}). "
                    "Consider slowing discretionary spending for the rest of the month."
                ),
                "category": "Overall Budget",
                "impact_level": "High",
            })

        # Rule 2: Category Budget Threshold Detection
        for b in budgets:
            cat = str(b.get("category") or "").strip()
            limit = float(b.get("monthly_limit") or 0.0)
            if not cat or limit <= 0:
                continue

            spent_in_cat = sum(
                float(e.get("amount") or 0.0)
                for e in expenses
                if str(e.get("category") or "").strip().lower() == cat.lower()
            )

            usage = (spent_in_cat / limit) * 100
            if usage >= 100:
                recommendations.append({
                    "title": f"Budget Exceeded in {cat} 🚨",
                    "message": (
                        f"You have spent {spent_in_cat:.2f} out of your {limit:.2f} limit "
                        f"({usage:.1f}% used). Freeze non-essential purchases in {cat}."
                    ),
                    "category": cat,
                    "impact_level": "High",
                })
            elif usage >= 80:
                recommendations.append({
                    "title": f"{cat} Budget Threshold Warning 🔔",
                    "message": (
                        f"You have reached {usage:.1f}% of your budget for {cat}. "
                        f"Only {limit - spent_in_cat:.2f} remains."
                    ),
                    "category": cat,
                    "impact_level": "Medium",
                })

        # Rule 3: Food & Dining Out Optimization
        food_spent = sum(
            float(e.get("amount") or 0.0)
            for e in expenses
            if str(e.get("category") or "").strip().lower() in ["food", "dining", "takeout", "groceries"]
        )
        if allowance > 0 and (food_spent / allowance) > 0.40:
            recommendations.append({
                "title": "Dining & Food Spending Opportunity 🍳",
                "message": (
                    f"Food makes up {round((food_spent / allowance) * 100, 1)}% of your allowance. "
                    "Cooking in your dorm/apartment or meal-prepping 2 extra days a week could save up to 20%."
                ),
                "category": "Food",
                "impact_level": "Medium",
            })

        # Rule 4: Savings Goal Acceleration
        for g in goals:
            current = float(g.get("current_amount") or 0.0)
            target = float(g.get("target_amount") or 0.0)
            status = g.get("status", "In Progress")
            if status == "In Progress" and target > 0:
                progress = (current / target) * 100
                if 80 <= progress < 100:
                    recommendations.append({
                        "title": f"Goal Almost Complete: {g.get('title')} 🎯",
                        "message": (
                            f"You are at {progress:.1f}% of your '{g.get('title')}' goal! "
                            f"Just {target - current:.2f} more to reach the finish line."
                        ),
                        "category": "Savings",
                        "impact_level": "Low",
                    })

        # Rule 5: Default positive advice if on good track
        if not recommendations:
            recommendations.append({
                "title": "Great Financial Health 🌱",
                "message": (
                    "Your spending is well within your budget limits and savings pace. "
                    "Keep building your emergency fund!"
                ),
                "category": "General",
                "impact_level": "Low",
            })

        return recommendations

    @classmethod
    def generate_rule_based_recommendations(
        cls,
        student_data: Dict[str, Any],
        expenses: List[Dict[str, Any]],
        budgets: List[Dict[str, Any]],
        goals: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return cls._generate_rule_based_recommendations(
            student_data=student_data,
            expenses=expenses,
            budgets=budgets,
            goals=goals,
        )
