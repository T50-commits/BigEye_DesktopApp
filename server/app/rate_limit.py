"""
BigEye Pro — Rate Limiter
Shared limiter instance for use across routers.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
