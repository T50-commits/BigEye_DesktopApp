"""
Client test fixtures — patches PySide6 imports where needed.
"""
import sys
import os
import pytest

# Ensure client/ is on sys.path (already done by root conftest, but be safe)
CLIENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "client")
if CLIENT_DIR not in sys.path:
    sys.path.insert(0, CLIENT_DIR)
