"""
auth.py — JWT authentication router with role-based access control.

Endpoints:
  POST /auth/register  — create a new user (stored in backend/users.json)
  POST /auth/login     — verify credentials, return signed JWT with role

Dependencies (importable by other routers):
  get_current_user()  — returns {"username": str, "role": str}
  get_admin_user()    — same but raises 403 if role != "admin"

Default accounts (auto-created on first startup if users.json is empty):
  admin / admin123  →  role: admin
  demo  / demo123   →  role: user
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt as _bcrypt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

SECRET_KEY                  = os.getenv("SECRET_KEY", "changeme")
ALGORITHM                   = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
SETUP_KEY                   = os.getenv("SETUP_KEY", "hospital_setup_2024")

# ---------------------------------------------------------------------------
# Persistent user store
# Schema: { username: { "hashed_password": str, "role": "admin"|"user" } }
# ---------------------------------------------------------------------------
USERS_FILE = Path(__file__).resolve().parents[3] / "backend" / "users.json"


def load_users() -> dict:
    if USERS_FILE.exists():
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(users: dict) -> None:
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def _seed_default_accounts() -> None:
    """Auto-create admin and demo accounts if the store is empty."""
    users = load_users()
    if users:
        return
    users["admin"] = {"hashed_password": _hash_password("admin123"), "role": "admin"}
    users["demo"]  = {"hashed_password": _hash_password("demo123"),  "role": "user"}
    save_users(users)
    print("Default accounts created: admin/admin123 (admin), demo/demo123 (user)")


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire  = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Seed on module load
# ---------------------------------------------------------------------------
_seed_default_accounts()

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class UserIn(BaseModel):
    username: str
    password: str
    role:     str = "user"


class TokenOut(BaseModel):
    access_token: str
    token_type:   str
    role:         str


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: Request, user: UserIn):
    users_db = load_users()

    if user.username in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    assigned_role = user.role if user.role in ("admin", "user") else "user"

    if assigned_role == "admin":
        setup_key_header = request.headers.get("X-Setup-Key", "")
        if setup_key_header != SETUP_KEY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid setup key. Contact your system administrator.",
            )

    users_db[user.username] = {
        "hashed_password": _hash_password(user.password),
        "role": assigned_role,
    }
    save_users(users_db)
    return {"message": "User registered successfully", "role": assigned_role}


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------
@router.post("/login", response_model=TokenOut)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    users_db = load_users()
    record   = users_db.get(form_data.username)

    if not record or not _verify_password(form_data.password, record["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role  = record["role"]
    token = _create_access_token(
        data={"sub": form_data.username, "role": role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": token, "token_type": "bearer", "role": role}


# ---------------------------------------------------------------------------
# Internal token decoder (shared by dependencies)
# ---------------------------------------------------------------------------
def _get_user_from_token(token: str) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role:     str = payload.get("role", "user")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if username not in load_users():
        raise credentials_exception

    return {"username": username, "role": role}


# ---------------------------------------------------------------------------
# get_current_user — any authenticated user
# ---------------------------------------------------------------------------
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    return _get_user_from_token(token)


# ---------------------------------------------------------------------------
# get_admin_user — admin only
# ---------------------------------------------------------------------------
def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
