"""
Authentication stub for local-first Scholia.

All routes return a hardcoded local user — no OAuth required.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["auth"])

LOCAL_USER = {
    "id": "local-user",
    "email": "local@localhost",
    "name": "Local User",
    "is_admin": True,
    "is_banned": False,
    "deleted_at": None,
}


async def require_auth():
    return LOCAL_USER


async def require_active():
    return LOCAL_USER


async def require_admin():
    return LOCAL_USER


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    isBanned: bool = False
    isAdmin: bool = False


@router.get("/me", response_model=UserResponse)
async def get_me():
    return UserResponse(
        id=LOCAL_USER["id"],
        email=LOCAL_USER["email"],
        name=LOCAL_USER["name"],
        isBanned=False,
        isAdmin=True,
    )
