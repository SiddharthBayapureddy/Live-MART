# Password Managements and Session Managements

import os
from datetime import datetime, timedelta, timezone  # Needed for Token expiration times
from typing import Optional

# For password hashing
from passlib.context import CryptContext

# For creating/decoding JWTs (JSON Web Tokens)
from jose import jwt, JWTError

# Importing schemas for token data
from schemas import CustomerRead, RetailerRead, WholesalerRead
from database import get_customer_by_email, get_retailer_by_email, get_wholesaler_by_email
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer


#--------------------------------------------------------------------------------------------------------------------------------------------

# 1. Managing Passwords

# Creating context for password hashing
password_context = CryptContext(schemes=["bcrypt"] , deprecated = "auto")   # "bcrypt" - Industry Standard 

# Returns the hashed password
def hash_password(password: str):
    return password_context.hash(password)


# Verifies the password
def verify_password(input_password: str , hashed_password: str):
    return password_context.verify(input_password , hashed_password)

#--------------------------------------------------------------------------------------------------------------------------------------------


# 2. JWT Token Configuration

# These should be in environment variables, but we'll hardcode for the project
SECRET_KEY = "your-super-secret-key-for-this-project" # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

# This defines the URL where the client will send a username/password to log in
# We will have three separate login URLs, but they all use the same token mechanism
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# This is a dependency that can be used to protect endpoints
# Note: You will likely need to create 3 separate dependencies:
# get_current_customer, get_current_retailer, get_current_wholesaler

# Example for getting a current customer
async def get_current_customer(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_mail: str = payload.get("sub")
        user_role: str = payload.get("role")
        if user_mail is None or user_role != "customer":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # In a real app, you'd run this in a threadpool
    user = get_customer_by_email(mail=user_mail) 
    if user is None:
        raise credentials_exception
    return user