from datetime import date
from typing import List, Dict, Any


class RecommendationEngine:
    """
    Intelligent recommendation engine analyzing student spending habits,
    budget boundaries, and goal targets to generate actionable advice.
    """

    @staticmethod
    def generate_recommendations(
        student_data: Dict[str, Any],
        expenses: List[Dict[str, Any]],
        budgets: List[Dict[str, Any]],
        goals: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        recommendations = []
        allowance = student_data.get("monthly_allowance", 0.0)
        total_spent = sum(e.get("amount", 0.0) for e in expenses)

        # Rule 1: High Burn Rate Check
        if allowance > 0 and total_spent > allowance * 0.75:
            burn_pct = round((total_spent / allowance) * 100, 1)
            recommendations.append({
                "title": "High Monthly Burn Rate Alert",
                "message": (
                    f"You have already spent {burn_pct}% of your monthly allowance ({allowance}). "
                    "Consider slowing discretionary spending for the rest of the month."
                ),
                "category": "Overall Budget",
                "impact_level": "High",
            })

        # Rule 2: Category Budget Threshold Detection
        for b in budgets:
            cat = b.get("category")
            limit = b.get("monthly_limit", 0.0)
            spent_in_cat = sum(
                e.get("amount", 0.0) for e in expenses if e.get("category", "").lower() == cat.lower()
            )
            if limit > 0:
                usage = (spent_in_cat / limit) * 100
                if usage >= 100:
                    recommendations.append({
                        "title": f"Budget Exceeded in {cat}",
                        "message": (
                            f"You have spent {spent_in_cat:.2f} out of your {limit:.2f} limit "
                            f"({usage:.1f}% used). Freeze non-essential purchases in {cat}."
                        ),
                        "category": cat,
                        "impact_level": "High",
                    })
                elif usage >= 80:
                    recommendations.append({
                        "title": f"{cat} Budget Threshold Warning",
                        "message": (
                            f"You have reached {usage:.1f}% of your budget for {cat}. "
                            f"Only {limit - spent_in_cat:.2f} remains."
                        ),
                        "category": cat,
                        "impact_level": "Medium",
                    })

        # Rule 3: Food & Dining Out Optimization
        food_spent = sum(
            e.get("amount", 0.0) for e in expenses if e.get("category", "").lower() in ["food", "dining", "takeout"]
        )
        if allowance > 0 and (food_spent / allowance) > 0.40:
            recommendations.append({
                "title": "Dining & Food Spending Opportunity",
                "message": (
                    f"Food makes up {round((food_spent / allowance) * 100, 1)}% of your allowance. "
                    "Cooking in your dorm/apartment or meal-prepping 2 extra days a week could save up to 20%."
                ),
                "category": "Food",
                "impact_level": "Medium",
            })

        # Rule 4: Savings Goal Acceleration
        for g in goals:
            current = g.get("current_amount", 0.0)
            target = g.get("target_amount", 0.0)
            status = g.get("status", "In Progress")
            if status == "In Progress" and target > 0:
                progress = (current / target) * 100
                if progress >= 80 and progress < 100:
                    recommendations.append({
                        "title": f"Goal Almost Complete: {g.get('title')}",
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
                "title": "Great Financial Health",
                "message": (
                    "Your spending is well within your budget limits and savings pace. "
                    "Keep building your emergency fund!"
                ),
                "category": "General",
                "impact_level": "Low",
            })

        return recommendations
