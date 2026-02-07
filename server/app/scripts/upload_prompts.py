"""
BigEye Pro — Upload Real Prompts & Dictionary to Firestore
Run: GOOGLE_APPLICATION_CREDENTIALS=./firebase-service-account.json python -m app.scripts.upload_prompts
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from google.cloud import firestore


# ── Paths to source files ──
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SPEC_DIR = os.path.join(BASE, "Design_Specification")
DICT_PATH = os.path.join(
    os.path.dirname(BASE),  # parent of BigEye_Desktop_App
    "Keywrod Gen all web_Pro_Private",
    "keywords_db.txt",
)

PROMPT_FILES = {
    "istock": os.path.join(SPEC_DIR, "prompt  iStock.md"),
    "hybrid": os.path.join(SPEC_DIR, "PROMPT HYBRID MODE.md"),
    "single": os.path.join(SPEC_DIR, "prompt Single words.md"),
}


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def upload():
    db = firestore.Client()
    doc_ref = db.collection("system_config").document("app_settings")

    # Read prompts
    prompts = {}
    for key, path in PROMPT_FILES.items():
        if not os.path.exists(path):
            print(f"❌ Prompt file not found: {path}")
            return
        content = read_file(path)
        prompts[key] = content
        print(f"✅ Loaded prompt_{key}: {len(content):,} bytes, {content.count(chr(10))+1} lines")

    # Read dictionary
    if not os.path.exists(DICT_PATH):
        print(f"❌ Dictionary file not found: {DICT_PATH}")
        return
    dictionary = read_file(DICT_PATH)
    words = [w.strip() for w in dictionary.strip().split("\n") if w.strip()]
    print(f"✅ Loaded dictionary: {len(words):,} words, {len(dictionary):,} bytes")

    # Upload to Firestore
    doc_ref.update({
        "prompts": {
            "istock": prompts["istock"],
            "hybrid": prompts["hybrid"],
            "single": prompts["single"],
        },
        "prompts_version": "v1",
        "prompts_updated_at": firestore.SERVER_TIMESTAMP,
        "dictionary": dictionary,
        "dictionary_version": "v1",
        "dictionary_updated_at": firestore.SERVER_TIMESTAMP,
        "dictionary_word_count": len(words),
    })

    print()
    print("=" * 50)
    print("✅ All prompts and dictionary uploaded to Firestore!")
    print(f"   prompt_istock: {len(prompts['istock']):,} bytes")
    print(f"   prompt_hybrid: {len(prompts['hybrid']):,} bytes")
    print(f"   prompt_single: {len(prompts['single']):,} bytes")
    print(f"   dictionary:    {len(words):,} words ({len(dictionary):,} bytes)")
    print("=" * 50)


if __name__ == "__main__":
    upload()
