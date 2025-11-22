from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlmodel import Session, select
from typing import Annotated

# Import your configuration and models safely here
from database import engine
from db_models import Customer, Retailer, Wholesaler
from auth import SECRET_KEY, ALGORITHM, bearer_scheme, get_customer_by_email, get_retailer_by_email, get_wholesaler_by_email

async def get_current_customer(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Customer:
    token = creds.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None or role != "customer":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    with Session(engine) as session:
        user = session.exec(select(Customer).where(Customer.email == email)).first()
        if user is None:
            raise credentials_exception
        return user

async def get_current_retailer(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Retailer:
    # Logic similar to above for retailer
    token = creds.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None or role != "retailer":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    with Session(engine) as session:
        user = session.exec(select(Retailer).where(Retailer.email == email)).first()
        if user is None:
            raise credentials_exception
        return user

# Add get_current_wholesaler here as well...