"""
Root conftest — adds both server/ and client/ to sys.path
so that imports like `from app.config import settings` and `from core.config import ...` work.
"""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_DIR = os.path.join(ROOT, "server")
CLIENT_DIR = os.path.join(ROOT, "client")

for p in (SERVER_DIR, CLIENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)
