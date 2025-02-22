# from fastapi import HTTPException, Depends, APIRouter
# from model import User
# from schema import UserCreate, TokenResponse, UserRegisterResponse
# from database import get_db
# from sqlalchemy.orm import Session
# from auth import hash_password, verify_password, create_access_token
# from fastapi.security import OAuth2PasswordRequestForm

# router = APIRouter()

# @router.post("/register", response_model=UserRegisterResponse)
# async def register(user: UserCreate, db: Session = Depends(get_db)):
#     """Route to register a new user"""
    
#     # Check if user already exists
#     existing_user = db.query(User).filter(User.username == user.username).first()
#     if existing_user:
#         raise HTTPException(status_code=400, detail="Username already exists")
    
#     # Hash the password
#     hashed_password = hash_password(user.password)

#     # Create new user
#     new_user = User(username=user.username, hashed_password=hashed_password)
#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)
    
#     return {"message": "User registered successfully", "username": new_user.username}

# @router.post("/login", response_model=TokenResponse)
# async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
#     """Route to authenticate user and return JWT token"""
    
#     # Check if user exists
#     user = db.query(User).filter(User.username == form_data.username).first()
#     if not user or not verify_password(form_data.password, user.hashed_password):
#         raise HTTPException(status_code=400, detail="Incorrect username or password")
    
#     # Generate JWT token (✅ Fix: passing a dictionary)
#     access_token = create_access_token({"sub": user.username})
    
#     return {"access_token": access_token, "token_type": "bearer"}




from fastapi import HTTPException, Depends, APIRouter, status
from model import User
from schema import UserCreate, TokenResponse, UserRegisterResponse
from database import get_db
from sqlalchemy.orm import Session
from auth import create_refresh_token, hash_password, create_access_token, authenticate_user, validate_refresh_token
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict

router = APIRouter()

@router.post("/register", response_model=UserRegisterResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Route to register a new user"""
    try:
        # Validate username length
        if len(user.username) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be at least 3 characters long"
            )
            
        # Validate password length
        if len(user.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == user.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Hash the password
        hashed_password = hash_password(user.password)

        # Create new user
        new_user = User(
            username=user.username, 
            hashed_password=hashed_password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "message": "User registered successfully",
            "username": new_user.username
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()  # Rollback on error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during registration: {str(e)}"
        ) from e

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