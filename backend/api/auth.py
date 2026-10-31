from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_api_key,
)
from backend.core.config import settings
from backend.schemas.auth import (
    UserCreate,
    UserLogin,
    TokenResponse,
    UserResponse,
    ApiKeyResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


def get_or_create_dev_user(db: Session) -> User:
    """Helper to ensure a default dev user exists for instant zero-friction use."""
    user = db.query(User).filter(User.email == settings.DEFAULT_USER_EMAIL).first()
    if not user:
        user = User(
            email=settings.DEFAULT_USER_EMAIL,
            hashed_password=hash_password(settings.DEFAULT_USER_PASSWORD),
            full_name="Default Developer",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate user via:
    1. Bearer JWT token
    2. X-API-Key header or Bearer cbk_live_...
    3. In development mode: Fallback to dev user if no credentials provided.
    """
    # 1. Check API Key header
    api_key = x_api_key
    if not api_key and auth and auth.credentials.startswith("cbk_live_"):
        api_key = auth.credentials

    if api_key:
        key_hash = hash_api_key(api_key)
        user = db.query(User).filter(User.api_key_hash == key_hash, User.is_active == True).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key.",
            )
        return user

    # 2. Check JWT Bearer token
    if auth and auth.credentials:
        payload = decode_access_token(auth.credentials)
        if payload and "sub" in payload:
            user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
            if user:
                return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        )

    # 3. Development mode fallback
    if settings.ENVIRONMENT == "development":
        return get_or_create_dev_user(db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide Bearer token or X-API-Key.",
    )


@router.post("/register", response_model=UserResponse)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""
    existing = db.query(User).filter(User.email == data.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered.")

    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        has_api_key=bool(user.api_key_hash),
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate with email and password to receive JWT token."""
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get authenticated user profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        has_api_key=bool(current_user.api_key_hash),
        created_at=current_user.created_at,
    )


@router.post("/api-key", response_model=ApiKeyResponse)
def create_api_key(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Generate or roll a new API key for external AI integration.
    Only the raw key is returned; its SHA-256 hash is saved to DB.
    """
    raw_key, hashed_key = generate_api_key()
    current_user.api_key_hash = hashed_key
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()

    return ApiKeyResponse(
        api_key=raw_key,
        message="Store this API key securely. It will not be shown again in plaintext.",
    )


@router.delete("/api-key")
def revoke_api_key(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Revoke the current API key."""
    current_user.api_key_hash = None
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "message": "API key revoked."}
