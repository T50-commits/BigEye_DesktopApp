"""
BigEye Pro — Initialize Firestore with default system_config
Run: python -m app.scripts.init_firestore
"""
import os
import sys

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from google.cloud import firestore


def init():
    db = firestore.Client()

    # Create system_config/app_settings
    doc_ref = db.collection("system_config").document("app_settings")

    if doc_ref.get().exists:
        print("system_config/app_settings already exists. Updating...")

    doc_ref.set({
        "prompts": {
            "prompt_istock": "You are an expert stock photo metadata specialist for iStock/Getty Images.",
            "prompt_hybrid": "You are an expert stock photo metadata specialist for Adobe Stock.",
            "prompt_single": "You are an expert stock photo metadata specialist for Shutterstock.",
            "user_prompt": "Analyze this image and generate metadata in JSON format with keys: title, description, keywords, category.",
        },
        "dictionary_url": "",
        "dictionary_hash": "",
        "blacklist": [
            "nike", "adidas", "puma", "reebok", "gucci", "louis vuitton",
            "chanel", "hermes", "rolex", "apple", "iphone", "ipad", "macbook",
            "samsung", "google", "microsoft", "coca cola", "pepsi",
            "starbucks", "mcdonalds", "disney", "marvel", "pokemon",
            "facebook", "instagram", "twitter", "tiktok", "youtube",
            "netflix", "spotify", "amazon", "tesla", "ferrari", "lamborghini",
            "bmw", "mercedes", "audi", "porsche", "toyota", "honda",
        ],
        "credit_rates": {
            "istock_photo": 3,
            "istock_video": 3,
            "adobe_photo": 2,
            "adobe_video": 2,
            "shutterstock_photo": 2,
            "shutterstock_video": 2,
        },
        "exchange_rate": 4,
        "app_latest_version": "2.0.0",
        "app_download_url": "",
        "app_update_notes": "",
        "force_update_below": "",
        "maintenance_mode": False,
        "maintenance_message": "",
        "context_cache_threshold": 20,
        "max_concurrent_images": 5,
        "max_concurrent_videos": 2,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })

    print("✅ system_config/app_settings initialized successfully")
    print(f"   Blacklist: {40} brand terms")
    print(f"   Credit rates: iStock=3, Adobe=2, Shutterstock=2")
    print(f"   Exchange rate: 1 THB = 4 credits")


if __name__ == "__main__":
    init()
