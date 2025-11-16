# Password Managements and Session Managements

import os
import hashlib # Use simple hashing
from datetime import datetime, timedelta, timezone
from typing import Optional

# For creating/decoding JWTs (JSON Web Tokens)
from jose import jwt, JWTError

# Importing schemas for token data
from schemas import CustomerRead, RetailerRead, WholesalerRead
from database import get_customer_by_email, get_retailer_by_email, get_wholesaler_by_email
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.concurrency import run_in_threadpool
from db_models import Customer, Retailer, Wholesaler


#--------------------------------------------------------------------------------------------------------------------------------------------

# 1. Managing Passwords (Simple hashlib.sha256)

# Returns the hashed password
def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


# Verifies the password
def verify_password(input_password: str , hashed_password: str):
    return hash_password(input_password) == hashed_password

#--------------------------------------------------------------------------------------------------------------------------------------------


# 2. JWT Token Configuration

# These should be in environment variables, but we'll hardcode for the project
SECRET_KEY = "your-super-secret-key-for-this-project" # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

# This tells FastAPI to look for the "Authorization: Bearer <token>" header
bearer_scheme = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency to get the current logged-in customer
async def get_current_customer(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Customer:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = creds.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_mail: str = payload.get("sub")
        user_role: str = payload.get("role")
        if user_mail is None or user_role != "customer":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await run_in_threadpool(get_customer_by_email, mail=user_mail) 
    if user is None:
        raise credentials_exception
    return user

# Dependency to get the current logged-in retailer
async def get_current_retailer(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Retailer:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = creds.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_mail: str = payload.get("sub")
        user_role: str = payload.get("role")
        if user_mail is None or user_role != "retailer":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await run_in_threadpool(get_retailer_by_email, mail=user_mail)
    if user is None:
        raise credentials_exception
    return user

# Dependency to get the current logged-in wholesaler
async def get_current_wholesaler(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Wholesaler:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = creds.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_mail: str = payload.get("sub")
        user_role: str = payload.get("role")
        if user_mail is None or user_role != "wholesaler":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await run_in_threadpool(get_wholesaler_by_email, mail=user_mail)
    if user is None:
        raise credentials_exception
    return user