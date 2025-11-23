# Password Managements and Session Managements

import os
from dotenv import load_dotenv
load_dotenv()

import hashlib # Use simple hashing
from datetime import datetime, timedelta, timezone
from typing import Optional

# For Google/Facebook OAuth
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

# For creating/decoding JWTs (JSON Web Tokens)
from jose import jwt, JWTError

# Importing schemas for token data
from schemas import CustomerRead, RetailerRead, WholesalerRead
from database import get_customer_by_email, get_retailer_by_email, get_wholesaler_by_email
from fastapi import Depends, HTTPException, status , BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.concurrency import run_in_threadpool
from db_models import Customer, Retailer, Wholesaler
from config import SECRET_KEY, ALGORITHM
#--------------------------------------------------------------------------------------------------------------------------------------------

# SMTP
import random
import string
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig , MessageType

# OTP Authentication 
def generate_otp() -> str:
    return "".join(random.choices(string.digits , k=6))

mail_config = ConnectionConfig(
    MAIL_USERNAME = os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD"),
    MAIL_FROM = os.getenv("MAIL_USERNAME"),
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)

async def send_otp_email(email: str , otp : str , background_tasks : BackgroundTasks):
    message = MessageSchema(
        subject="Live MART - Password Reset OTP" , 
        recipients=[email],
        body = f"""
        <h3>Password Reset Request</h3>
        <p>Your OTP for resetting your password is:</p>
        <h1 style='color: #FF4B2B;'>{otp}</h1>
        <p>This OTP is valid for 10 minutes.</p>
        <p>If you did not request this, please ignore this email.</p>
        """,
        subtype=MessageType.html
    )

    fm = FastMail(mail_config)
    background_tasks.add_task(fm.send_message , message)


async def send_verification_email(email: str, otp: str, background_tasks: BackgroundTasks):
    message = MessageSchema(
        subject="Live MART - Verify your Account",
        recipients=[email],
        body=f"""
        <h3>Welcome to Live MART!</h3>
        <p>Please verify your email address to activate your account.</p>
        <p>Your Verification OTP is:</p>
        <h1 style='color: #4CAF50;'>{otp}</h1>
        <p>This OTP is valid for 30 minutes.</p>
        """,
        subtype=MessageType.html
    )

    fm = FastMail(mail_config)
    background_tasks.add_task(fm.send_message, message)


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

#--------------------------------------------------------------------------------------------------------------------------------------------

# 3. Google Auth Configuration
oauth = OAuth()

oauth.register(
    name = "google",
    client_id = os.getenv("GOOGLE_CLIENT_ID"),
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET_KEY"),
    server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs = {
        'scope' : 'openid email profile'
    }
)

#--------------------------------------------------------------------------------------------------------------------------------------------

# In auth.py

async def send_admin_query_email(form_data: dict, background_tasks: BackgroundTasks):
    # Email to the Admin
    message = MessageSchema(
        subject=f"New Query: {form_data['subject']}",
        recipients=["livemart.bphc@gmail.com"], # Admin Email
        body=f"""
        <h3>New Customer Query</h3>
        <p><b>Name:</b> {form_data['name']}</p>
        <p><b>Email:</b> {form_data['email']}</p>
        <hr>
        <p>{form_data['message']}</p>
        """,
        subtype=MessageType.html
    )
    fm = FastMail(mail_config)
    background_tasks.add_task(fm.send_message, message)