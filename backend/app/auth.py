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



async def send_order_confirmation_email(
    email: str, 
    name: str, 
    order_id: int, 
    total_price: float, 
    items: list, 
    address: str, 
    background_tasks: BackgroundTasks
):
    """
    Sends an HTML order confirmation email to the customer.
    'items' should be a list of dicts: [{'name': '...', 'qty': 1, 'price': 100}, ...]
    """
    
    # 1. Build HTML Table Rows for Items
    items_html = ""
    for i in items:
        items_html += f"""
        <tr>
            <td style='padding:8px; border-bottom:1px solid #eee;'>{i['name']}</td>
            <td style='padding:8px; border-bottom:1px solid #eee; text-align:center;'>{i['qty']}</td>
            <td style='padding:8px; border-bottom:1px solid #eee; text-align:right;'>₹{i['price']}</td>
        </tr>
        """

    # 2. Construct Email Body
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #000; color: #fff; padding: 20px; text-align: center;">
            <h2 style="margin:0; color: #00f3ff;">Order Confirmed!</h2>
            <p style="margin:5px 0 0;">Thank you for shopping with Live MART.</p>
        </div>
        
        <div style="padding: 20px;">
            <p>Hi <b>{name}</b>,</p>
            <p>We have received your order <b>#{order_id}</b> and it is now being processed.</p>
            
            <h3 style="border-bottom: 2px solid #00f3ff; padding-bottom: 5px; margin-top: 20px;">Order Summary</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <tr style="background: #f9f9f9;">
                    <th style="padding:8px; text-align:left;">Product</th>
                    <th style="padding:8px; text-align:center;">Qty</th>
                    <th style="padding:8px; text-align:right;">Price</th>
                </tr>
                {items_html}
                <tr>
                    <td colspan="2" style="padding:10px; text-align:right; font-weight:bold;">Total Amount:</td>
                    <td style="padding:10px; text-align:right; font-weight:bold; color: #00f3ff; font-size: 16px;">₹{total_price}</td>
                </tr>
            </table>
            
            <div style="background: #f9f9f9; padding: 10px; margin-top: 20px; border-radius: 4px;">
                <h4 style="margin: 0 0 5px;">Shipping Address</h4>
                <p style="margin: 0; font-size: 13px; color: #555;">{address}</p>
            </div>
            
            <p style="margin-top: 30px; font-size: 12px; color: #888; text-align: center;">
                If you have any questions, simply reply to this email.<br>
                &copy; 2025 Live MART
            </p>
        </div>
    </div>
    """

    # 3. Send Message
    message = MessageSchema(
        subject=f"Order Confirmation - #{order_id}",
        recipients=[email],
        body=body,
        subtype=MessageType.html
    )
    
    fm = FastMail(mail_config)
    background_tasks.add_task(fm.send_message, message)



# ----------------------------------------------------------------------------------------------------------------------------

async def send_status_update_email(
    email: str, 
    name: str, 
    order_id: int, 
    new_status: str, 
    background_tasks: BackgroundTasks
):
    """
    Sends a simple status update email.
    """
    
    # Map status to a color/emoji
    status_color = "#00f3ff"
    if new_status == "Shipped":
        status_color = "#ff9800"
    elif new_status == "Delivered":
        status_color = "#4CAF50"

    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; background: #000; color: #fff;">
        <div style="background-color: {status_color}; color: #000; padding: 15px; text-align: center;">
            <h2 style="margin:0; font-size: 20px;">Order #{order_id} Update!</h2>
        </div>
        
        <div style="padding: 20px; background: #1a1a1a;">
            <p>Hi <b>{name}</b>,</p>
            <p>There's an update regarding your recent order:</p>
            
            <h3 style="color: {status_color};">New Status: {new_status.upper()}</h3>
            
            <p>Your order is now: <b>{new_status}</b>.</p>
            
            { 'If your order has been shipped, please allow 3-5 days for delivery.' if new_status == 'Shipped' else ''}
            
            <p style="margin-top: 30px; font-size: 12px; color: #888;">
                Thank you for your business.<br>
                &copy; 2025 Live MART
            </p>
        </div>
    </div>
    """

    message = MessageSchema(
        subject=f"Order Update: #{order_id} is now {new_status}",
        recipients=[email],
        body=body,
        subtype=MessageType.html
    )
    
    fm = FastMail(mail_config)
    background_tasks.add_task(fm.send_message, message)