import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import get_settings

settings = get_settings()
security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=settings.JWT_EXPIRATION_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def generate_api_key() -> str:
    import secrets
    return "cs2_" + secrets.token_urlsafe(32)

async def get_current_user(request: Request):
    from app.db.database import SessionLocal
    from app.models.models import User
    
    # Check session cookie first
    token = request.cookies.get("access_token")
    
    # Fall back to Authorization header
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if not token:
        return None
    
    payload = decode_token(token)
    if not payload:
        return None
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == payload.get("user_id")).first()
        return user
    finally:
        db.close()

async def require_auth(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

async def get_current_user_api_key(request: Request):
    """Authenticate via API key for API endpoints."""
    from app.db.database import SessionLocal
    from app.models.models import User
    
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        # Fall back to Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = decode_token(token)
            if payload:
                db = SessionLocal()
                try:
                    return db.query(User).filter(User.id == payload.get("user_id")).first()
                finally:
                    db.close()
        return None
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.api_key == api_key).first()
        return user
    finally:
        db.close()

async def require_api_key(request: Request):
    user = await get_current_user_api_key(request)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account inactive")
    return user
