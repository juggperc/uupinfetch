from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timezone
from app.db.database import get_db
from app.models.models import User
from app.core.auth import (
    hash_password, verify_password, create_access_token, generate_api_key,
    get_current_user, require_auth
)
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    subscription_plan: str
    subscription_status: str
    api_calls_total: int
    api_calls_month: int
    api_key: Optional[str]
    
    class Config:
        from_attributes = True

@router.post("/register")
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name or data.email.split("@")[0],
        api_key=generate_api_key(),
        api_key_created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token({"user_id": user.id, "email": user.email})
    return {"access_token": token, "user": UserResponse.model_validate(user)}

@router.post("/login")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"user_id": user.id, "email": user.email})
    return {"access_token": token, "user": UserResponse.model_validate(user)}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(require_auth)):
    return UserResponse.model_validate(user)

@router.post("/api-key/regenerate")
async def regenerate_api_key(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    user.api_key = generate_api_key()
    user.api_key_created_at = datetime.now(timezone.utc)
    db.commit()
    return {"api_key": user.api_key}

@router.get("/session")
async def check_session(request: Request):
    user = await get_current_user(request)
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "user": UserResponse.model_validate(user)}
