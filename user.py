from fastapi import HTTPException, Depends, APIRouter, status, Response
from model import User
from schema import UserCreate, TokenResponse, UserRegisterResponse
from database import get_db
from sqlalchemy.orm import Session
from auth import create_refresh_token, hash_password, create_access_token, authenticate_user, validate_refresh_token
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict
from datetime import timedelta


router = APIRouter()
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour


@router.post("/register", response_model=UserRegisterResponse)
async def register(user: UserCreate, response: Response, db: Session = Depends(get_db)):
    """Register a new user and return a JWT token"""
    try:
        # Validate username length
        if len(user.username) < 3:
            raise HTTPException(status_code=400, detail="Username must be at least 3 characters long")

        # Validate password length
        if len(user.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

        # Check if user exists
        existing_user = db.query(User).filter(User.username == user.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Hash the password and create the user
        hashed_password = hash_password(user.password)
        new_user = User(username=user.username, hashed_password=hashed_password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # ✅ Generate access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": new_user.username}, expires_delta=access_token_expires)

        # ✅ Set token in an HTTP-only cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,  # Use `False` in development
            samesite="Lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        return {
            "message": "User registered successfully",
            "username": new_user.username,
            "access_token": access_token,
            "token_type": "Bearer"
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}") from e


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Dict:
    """Route to authenticate user and return JWT token"""
    try:
        # Authenticate user
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Generate access and refresh tokens
        access_token = create_access_token(data={"sub": user.username})
        refresh_token = create_refresh_token(data={"sub": user.username})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "username": user.username
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}"
        )

# Add a refresh token endpoint
@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
) -> Dict:
    """Route to refresh access token using refresh token"""
    try:
        # Validate refresh token
        payload = validate_refresh_token(refresh_token)
        username = payload.get("sub")
        
        # Get user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
            
        # Generate new access token
        access_token = create_access_token(data={"sub": username})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,  # Return same refresh token
            "token_type": "bearer",
            "username": username
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing token: {str(e)}"
        )