"""
AI Expense Categorization Engine with Personalized Feedback Learning.
Implements a 3-tier categorization hierarchy:
1. User-Learned Preferences (Highest Priority - Personalized)
2. Comprehensive Rule-Based Heuristic Dictionary (Fast, Deterministic)
3. Groq Generative AI Classification (Flexible, Handles Novel Merchants)
"""
import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import CategoryPreference

logger = logging.getLogger(__name__)

# Canonical categories
CATEGORIES = [
    "Food",
    "Groceries",
    "Transport",
    "Shopping",
    "Education",
    "Entertainment",
    "Bills & Utilities",
    "Healthcare",
    "Subscriptions",
    "Travel",
    "Personal Care",
    "Other",
]

# Comprehensive Indian student-focused merchant and keyword dictionary
HEURISTIC_RULES: Dict[str, Tuple[str, str]] = {
    # Food & Food Delivery
    "zomato": ("Food", "Food Delivery"),
    "swiggy": ("Food", "Food Delivery"),
    "mcdonald": ("Food", "Fast Food"),
    "burger king": ("Food", "Fast Food"),
    "kfc": ("Food", "Fast Food"),
    "dominos": ("Food", "Pizza"),
    "pizza hut": ("Food", "Pizza"),
    "subway": ("Food", "Fast Food"),
    "starbucks": ("Food", "Coffee & Cafe"),
    "cafe coffee day": ("Food", "Coffee & Cafe"),
    "ccd": ("Food", "Coffee & Cafe"),
    "chai point": ("Food", "Tea & Snacks"),
    "chaayos": ("Food", "Tea & Snacks"),
    "canteen": ("Food", "Campus Canteen"),
    "mess": ("Food", "Hostel Mess"),
    "dhaba": ("Food", "Dining"),
    "restaurant": ("Food", "Dining"),
    "baker": ("Food", "Bakery"),
    "haldiram": ("Food", "Sweets & Snacks"),

    # Groceries & Quick Commerce
    "blinkit": ("Groceries", "Quick Commerce"),
    "zepto": ("Groceries", "Quick Commerce"),
    "instamart": ("Groceries", "Quick Commerce"),
    "bigbasket": ("Groceries", "Supermarket"),
    "dmart": ("Groceries", "Supermarket"),
    "reliance fresh": ("Groceries", "Supermarket"),
    "nature's basket": ("Groceries", "Gourmet"),
    "kirana": ("Groceries", "Local Store"),
    "supermarket": ("Groceries", "Supermarket"),
    "vegetable": ("Groceries", "Fresh Produce"),
    "fruit": ("Groceries", "Fresh Produce"),
    "milk": ("Groceries", "Dairy"),

    # Transport & Commute
    "uber": ("Transport", "Cab"),
    "ola": ("Transport", "Cab"),
    "rapido": ("Transport", "Bike Taxi"),
    "metro": ("Transport", "Public Transit"),
    "dmrc": ("Transport", "Metro"),
    "bmrc": ("Transport", "Metro"),
    "irctc": ("Transport", "Railways"),
    "indian railways": ("Transport", "Railways"),
    "petrol": ("Transport", "Fuel"),
    "fuel": ("Transport", "Fuel"),
    "hpcl": ("Transport", "Fuel"),
    "bpcl": ("Transport", "Fuel"),
    "ioc": ("Transport", "Fuel"),
    "shell": ("Transport", "Fuel"),
    "auto": ("Transport", "Auto Rickshaw"),
    "toll": ("Transport", "Toll"),

    # Shopping
    "amazon": ("Shopping", "E-Commerce"),
    "flipkart": ("Shopping", "E-Commerce"),
    "myntra": ("Shopping", "Apparel"),
    "meesho": ("Shopping", "E-Commerce"),
    "ajio": ("Shopping", "Apparel"),
    "zara": ("Shopping", "Fashion"),
    "h&m": ("Shopping", "Fashion"),
    "uniqlo": ("Shopping", "Fashion"),
    "nykaa": ("Shopping", "Cosmetics"),
    "tata cliq": ("Shopping", "E-Commerce"),
    "decathlon": ("Shopping", "Sports"),

    # Education & Campus
    "coursera": ("Education", "Online Course"),
    "udemy": ("Education", "Online Course"),
    "edx": ("Education", "Online Course"),
    "chegg": ("Education", "Study Tools"),
    "xerox": ("Education", "Printing & Stationery"),
    "photocopy": ("Education", "Printing & Stationery"),
    "print": ("Education", "Printing"),
    "stationery": ("Education", "Stationery"),
    "book": ("Education", "Books"),
    "tuition": ("Education", "Tuition Fee"),
    "college": ("Education", "Academic Fees"),
    "university": ("Education", "Academic Fees"),
    "library": ("Education", "Library"),

    # Entertainment & Gaming
    "netflix": ("Entertainment", "Streaming"),
    "spotify": ("Entertainment", "Music Streaming"),
    "youtube": ("Entertainment", "Video"),
    "prime video": ("Entertainment", "Streaming"),
    "hotstar": ("Entertainment", "Streaming"),
    "pvr": ("Entertainment", "Cinema"),
    "inox": ("Entertainment", "Cinema"),
    "cinepolis": ("Entertainment", "Cinema"),
    "bookmyshow": ("Entertainment", "Movies & Events"),
    "steam": ("Entertainment", "Gaming"),
    "playstation": ("Entertainment", "Gaming"),
    "gaming": ("Entertainment", "Gaming"),

    # Bills & Utilities
    "electricity": ("Bills & Utilities", "Power"),
    "water": ("Bills & Utilities", "Water"),
    "gas": ("Bills & Utilities", "Gas"),
    "airtel": ("Bills & Utilities", "Mobile/Broadband"),
    "jio": ("Bills & Utilities", "Mobile/Broadband"),
    "vodafone": ("Bills & Utilities", "Mobile"),
    "vi": ("Bills & Utilities", "Mobile"),
    "recharge": ("Bills & Utilities", "Mobile Recharge"),
    "wifi": ("Bills & Utilities", "Internet"),
    "broadband": ("Bills & Utilities", "Internet"),

    # Healthcare & Pharmacy
    "apollo": ("Healthcare", "Pharmacy"),
    "1mg": ("Healthcare", "Pharmacy"),
    "pharmacy": ("Healthcare", "Medicine"),
    "medical": ("Healthcare", "Medical Store"),
    "hospital": ("Healthcare", "Hospital"),
    "clinic": ("Healthcare", "Consultation"),
    "practo": ("Healthcare", "Doctor"),
    "dentist": ("Healthcare", "Dental"),

    # Subscriptions
    "apple.com/bill": ("Subscriptions", "Apple Services"),
    "google play": ("Subscriptions", "App Services"),
    "openai": ("Subscriptions", "AI Tools"),
    "chatgpt": ("Subscriptions", "AI Tools"),
    "github": ("Subscriptions", "Developer Tools"),
    "icloud": ("Subscriptions", "Cloud Storage"),
    "google one": ("Subscriptions", "Cloud Storage"),

    # Travel
    "makemytrip": ("Travel", "Booking"),
    "goibibo": ("Travel", "Booking"),
    "cleartrip": ("Travel", "Booking"),
    "oyo": ("Travel", "Lodging"),
    "hotel": ("Travel", "Lodging"),
    "airbnb": ("Travel", "Lodging"),
    "indigo": ("Travel", "Airlines"),
    "air india": ("Travel", "Airlines"),

    # Personal Care
    "salon": ("Personal Care", "Hair & Grooming"),
    "parlour": ("Personal Care", "Grooming"),
    "barber": ("Personal Care", "Haircut"),
    "spa": ("Personal Care", "Wellness"),
    "gym": ("Personal Care", "Fitness"),
    "cult": ("Personal Care", "Fitness"),
}


class TransactionCategorizer:
    """
    Intelligent categorizer evaluating user preferences, deterministic dictionaries,
    and Groq AI to classify financial expenses.
    """

    @classmethod
    def categorize(
        cls,
        merchant: str,
        amount: float,
        description: Optional[str] = None,
        student_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Categorize a transaction.
        Returns {
            "category": str,
            "subcategory": Optional[str],
            "confidence": float,  # 0.0 to 1.0
            "method": "user_preference" | "heuristic" | "groq_ai" | "fallback"
        }
        """
        normalized_merchant = (merchant or "").strip().lower()

        # -------------------------------------------------------------
        # Tier 1: Check User-Learned Preferences
        # -------------------------------------------------------------
        if student_id and db and normalized_merchant:
            prefs = (
                db.query(CategoryPreference)
                .filter(CategoryPreference.student_id == student_id)
                .all()
            )
            for pref in prefs:
                kw = (pref.merchant_keyword or "").strip().lower()
                if kw and (kw in normalized_merchant or normalized_merchant in kw):
                    return {
                        "category": pref.preferred_category,
                        "subcategory": pref.preferred_subcategory or "User Custom",
                        "confidence": 1.0,
                        "method": "user_preference",
                    }

        # -------------------------------------------------------------
        # Tier 2: Deterministic Rule-Based Heuristics
        # -------------------------------------------------------------
        heuristic_match = cls._match_heuristic(normalized_merchant, description)
        if heuristic_match:
            category, subcategory = heuristic_match
            return {
                "category": category,
                "subcategory": subcategory,
                "confidence": 0.95,
                "method": "heuristic",
            }

        # -------------------------------------------------------------
        # Tier 3: Groq Generative AI (if API key configured)
        # -------------------------------------------------------------
        groq_key = os.getenv("GROQ_API_KEY") or (settings.groq_api_key if settings and hasattr(settings, "groq_api_key") else "")
        api_key = groq_key.strip() if groq_key else ""

        if api_key and "invalid" not in api_key.lower():
            try:
                ai_result = cls._categorize_with_groq(
                    api_key=api_key,
                    merchant=merchant,
                    amount=amount,
                    description=description,
                )
                if ai_result:
                    return ai_result
            except Exception as e:
                logger.warning(f"Groq AI categorization failed: {e}. Defaulting to fallback category.")

        # -------------------------------------------------------------
        # Fallback: General / Other
        # -------------------------------------------------------------
        return {
            "category": "Other",
            "subcategory": "General Expense",
            "confidence": 0.50,
            "method": "fallback",
        }

    @classmethod
    def _match_heuristic(cls, normalized_merchant: str, description: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """Look for keywords in merchant and description against dictionary."""
        combined = f"{normalized_merchant} {(description or '').lower()}".strip()
        for keyword, (cat, subcat) in HEURISTIC_RULES.items():
            if keyword in combined:
                return cat, subcat
        return None

    @classmethod
    def _categorize_with_groq(
        cls,
        api_key: str,
        merchant: str,
        amount: float,
        description: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Use Groq Llama3/GPT models to categorize unseen merchants."""
        model = getattr(settings, "groq_model", "llama-3.3-70b-versatile") or "llama-3.3-70b-versatile"
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "SmartFinanceAI/1.0"
        }

        prompt = f"""
You are a financial classification AI for a student finance tracker.
Classify this financial expense into ONE of these allowed categories:
{json.dumps(CATEGORIES)}

Transaction Details:
- Merchant/Party: {merchant}
- Amount: ₹{amount:.2f}
- Details: {description or 'N/A'}

Return strictly a JSON object with this exact schema:
{{
  "category": "One of allowed categories",
  "subcategory": "Specific subcategory e.g. Dining, Textbooks, Metro",
  "confidence": 0.85
}}
"""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }

        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.warning(f"Groq API ({model}) returned status code {resp.status_code}: {resp.text[:200]}")
                    return None
                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return None
                content_text = choices[0]["message"]["content"]
                if "```" in content_text:
                    content_text = content_text.split("```")[1]
                    if content_text.startswith("json"):
                        content_text = content_text[4:]
                res_obj = json.loads(content_text.strip())
                cat = str(res_obj.get("category") or "Other").strip()
                if cat not in CATEGORIES:
                    cat = "Other"
                subcat = str(res_obj.get("subcategory") or "General Expense").strip()
                confidence = float(res_obj.get("confidence") or 0.85)
                return {
                    "category": cat,
                    "subcategory": subcat,
                    "confidence": round(max(0.10, min(1.0, confidence)), 2),
                    "method": "groq_ai",
                }
        except Exception as e:
            logger.warning(f"Groq categorization error: {e}")
            return None
None
