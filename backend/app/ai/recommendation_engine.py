import os
import json
import logging
from typing import List, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Intelligent recommendation engine analyzing student spending habits,
    budget boundaries, and goal targets.
    
    Uses Google Gemini Generative AI when GEMINI_API_KEY is configured,
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
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key != "your_gemini_api_key_here":
            try:
                gemini_recs = cls._generate_gemini_recommendations(
                    api_key=api_key,
                    student_data=student_data,
                    expenses=expenses,
                    budgets=budgets,
                    goals=goals,
                )
                if gemini_recs and len(gemini_recs) > 0:
                    return gemini_recs
            except Exception as e:
                logger.warning(f"Gemini API recommendation error: {e}. Falling back to rule-based engine.")

        # Fallback to heuristic rule engine
        return cls._generate_rule_based_recommendations(
            student_data=student_data,
            expenses=expenses,
            budgets=budgets,
            goals=goals,
        )

    @classmethod
    def _generate_gemini_recommendations(
        cls,
        api_key: str,
        student_data: Dict[str, Any],
        expenses: List[Dict[str, Any]],
        budgets: List[Dict[str, Any]],
        goals: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

        allowance = float(student_data.get("monthly_allowance") or 0.0)
        currency = str(student_data.get("currency") or "USD")
        student_name = str(student_data.get("name") or "Student")
        total_spent = sum(float(e.get("amount") or 0.0) for e in expenses)

        # Build financial summary for prompt
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
                for e in expenses[-15:]  # last 15 expenses
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

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.4,
            },
        }

        with httpx.Client(timeout=12.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning(f"Gemini API returned status code {resp.status_code}: {resp.text[:200]}")
                return []

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return []

            content_text = candidates[0]["content"]["parts"][0]["text"]
            parsed_recs = json.loads(content_text)

            # Validate list structure
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
            return clean_recs

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
