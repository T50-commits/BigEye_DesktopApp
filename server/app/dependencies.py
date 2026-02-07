"""
BigEye Pro — FastAPI Dependencies
Auth dependency for protected endpoints.
"""
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.security import decode_jwt_token
from app.database import users_ref

logger = logging.getLogger("bigeye-api")

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Validate JWT token and return user dict.
    Raises 401 if token is invalid or user not found.
    """
    token = credentials.credentials
    try:
        payload = decode_jwt_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    # Fetch user from Firestore
    doc = users_ref().document(user_id).get()
    if not doc.exists:
        raise HTTPException(status_code=401, detail="User not found")

    user = doc.to_dict()
    user["user_id"] = doc.id

    if user.get("status") == "banned":
        raise HTTPException(status_code=403, detail="Account suspended")

    return user
