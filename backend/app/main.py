# App


# Importing FastAPI
from fastapi import FastAPI , HTTPException , status, Depends, Form , BackgroundTasks,UploadFile,File

from typing import List, Annotated, Optional 
from pydantic import BaseModel 
import shutil 
import uuid 
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session, select, or_ , col
from contextlib import asynccontextmanager

from fastapi.concurrency import run_in_threadpool

# Add datetime for Google Auth
from datetime import datetime, timedelta

from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse
import os
from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel # Importing BaseModel for the new Verification Schema

from auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    get_current_retailer,
    get_current_customer,
    get_current_wholesaler,

    oauth, # Google OAuth

    # SMPT OTP Config
    send_otp_email,
    send_verification_email, # <--- NEW: Imported for signup verification
    generate_otp
)

# Importing custom-built database models and functions
from database import (
    create_db_and_tables,
    add_customer,
    add_product,
    add_retailer,
    add_wholesaler,
    create_cart_for_customer,
    add_item_to_cart,
    get_cart_items,
    get_cart_size,
    get_customer_by_email,
    get_retailer_by_email,
    get_wholesaler_by_email,
    get_cart_by_customer_id,
    get_detailed_cart_items,
    process_checkout,
    get_products_by_retailer,
    get_product_by_id,
    update_product_details,
    get_orders_by_retailer,
    get_order_by_id,
    update_order_status,
    
    # Verification Database Functions
    save_verification_otp, # <--- NEW
    verify_user_account,   # <--- NEW

    engine
)

# Importing the SQLModel classes
from db_models import (Customer, 
                       Product, 
                       ShoppingCart,
                        ShoppingCartItem, 
                        Retailer,
                        Wholesaler ,
                        WholesaleOrder,
                        PasswordReset, 
                        OrderRecords,
                        Category,
                        OrderItem,
                        WholesaleOrderItem,
                    
                        )

# Importing the Schemas
from schemas import *

# Image Management
import shutil
from fastapi import File , UploadFile
# -----------------------------
# Building the App
# -----------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_db_and_tables()
    yield

app = FastAPI(
    title="Live MART" , 
    lifespan=lifespan
)

SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-random-string-for-dev")
app.add_middleware(SessionMiddleware , secret_key = SECRET_KEY)


# Mounting the app to folder at "../data"
# app.mount("/static" , StaticFiles(directory="../data") , name="static") # Removed relative path causing issues

# Creating endpoints

# Root 
@app.get("/")
def root():
    # This will now be overridden by the StaticFiles mount if you have an index.html
    return "Hello Word!"



# -------------------------------------------------------------------------------------------------------------------------------------------------
# --- Customer Auth Endpoints ---
# -------------------------------------------------------------------------------------------------------------------------------------------------

# Signup Endpoint - POST  ---> Accepts JSON Body (CustomerCreate) and returns CustomerRead
@app.post("/signup/customer" , response_model=CustomerRead , status_code=status.HTTP_201_CREATED, tags=["Customer Auth"])   # Returns 201 on Success
async def signup_customer(
    customer : CustomerCreate,
    background_tasks: BackgroundTasks # <--- NEW: Required for sending email
):

    # Check if email already exists
    exists = await run_in_threadpool(get_customer_by_email, customer.mail)

    if exists:
        raise HTTPException(status_code=400 , detail="Email Already Registered")

    # Hashing the password
    hashed_password = hash_password(customer.password)

    new_customer = await run_in_threadpool(
        add_customer,
        customer.name,
        customer.mail,
        hashed_password,
        customer.delivery_address,
        customer.city,  
        customer.state,
        customer.pincode,
        customer.phone_number,
        lat=customer.lat,
        lon=customer.lon
    )

    # If customer not created
    if not new_customer:
        raise HTTPException(status_code=500 , detail="Failed to create Customer. Oops, Try again!")

    # --- NEW: Send Verification OTP ---
    otp = generate_otp()
    await run_in_threadpool(save_verification_otp, customer.mail, otp)
    await send_verification_email(customer.mail, otp, background_tasks)
    # ----------------------------------

    # Used Custom Read to serialize response (orm_mode = True)
    return new_customer 

# -------------------------------------------------------------------------------------------------------------------------------------------------

# Login Endpoint - POST ---> Accepts JSON Body
@app.post("/login/customer", response_model=Token, tags=["Customer Auth"])
async def login_customer(
    req: LoginRequest
):

    # Checking if customer exists
    customer = await run_in_threadpool(get_customer_by_email , req.mail)

    if not customer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail="Invalid Credentials: Mail not found")
    
    # --- NEW: Verify if account is active ---
    if not customer.is_verified:
        raise HTTPException(status_code=403, detail="Account not verified. Please verify your email.")
    # ----------------------------------------

    # Checking password
    # Password incorrect
    if not verify_password(req.password, customer.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail="Invalid Credentials: Password not found")
    
    # Create and return JWT token
    access_token = create_access_token(data={"sub": customer.mail, "role": "customer"})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/customer/me", response_model=CustomerRead, tags=["Customer Auth"])
async def get_me(customer: Customer = Depends(get_current_customer)):
    return customer

# -------------------------------------------------------------------
# --- NEW: Customer Profile Updates (Fix for Edit Profile Page) ---
# -------------------------------------------------------------------

# Schema for name update
class CustomerNameUpdate(BaseModel):
    name: str

@app.patch("/customer/me/update", response_model=CustomerRead, tags=["Customer Auth"])
async def update_customer_name(
    update_data: CustomerNameUpdate,
    current_customer: Customer = Depends(get_current_customer)
):
    with Session(engine) as session:
        # Fetch from DB to ensure we have the latest object attached to session
        customer_db = session.get(Customer, current_customer.id)
        if not customer_db:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Update field
        customer_db.name = update_data.name
        
        session.add(customer_db)
        session.commit()
        session.refresh(customer_db)
        return customer_db

@app.post("/customer/me/upload-pfp", tags=["Customer Auth"])
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_customer: Customer = Depends(get_current_customer)
):
    # 1. Define the location (Matches your Static Mount logic)
    # base_dir/../data/profile_pictures
    base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_dir = os.path.join(base_dir, "../data/profile_pictures")
    os.makedirs(upload_dir, exist_ok=True)
    
    # 2. Generate unique filename
    file_extension = file.filename.split(".")[-1]
    new_filename = f"{current_customer.id}_{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(upload_dir, new_filename)
    
    # 3. Save file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 4. Update DB with the relative URL
    # The static mount is at /profile_pictures, so the URL is "profile_pictures/filename"
    relative_url = f"profile_pictures/{new_filename}"
    
    with Session(engine) as session:
        customer_db = session.get(Customer, current_customer.id)
        
        # FIX: Change 'image_url' to 'profile_pic'
        customer_db.profile_pic = relative_url 
        
        session.add(customer_db)
        session.commit()
        
    return {"image_url": relative_url}

# --- UPDATED ENDPOINT: Get Cart (Auto-creates if missing) ---
@app.get("/cart", response_model=CartRead, tags=["Cart & Checkout"])
async def get_customer_cart(
    customer: Customer = Depends(get_current_customer)
):
    # Try to find existing cart
    cart = await run_in_threadpool(get_cart_by_customer_id, customer_id=customer.id)
    
    # FIX: If cart doesn't exist, create it now instead of returning 404
    if not cart:
        cart = await run_in_threadpool(create_cart_for_customer, customer_id=customer.id)
        
    detailed_items = await run_in_threadpool(get_detailed_cart_items, cart_id=cart.id)
    
    # Calculate total size safely
    total_size = sum(item['quantity'] for item in detailed_items)
    
    return {"items": detailed_items, "total_size": total_size}



# Cart items of the customer
# In main.py

# In main.py

# FIND AND REPLACE THE ENTIRE 'get_my_orders' FUNCTION WITH THIS:

@app.get("/customer/orders", response_model=List[OrderRecordsRead], tags=["Cart & Checkout"])
def get_my_orders(customer: Customer = Depends(get_current_customer)):
    with Session(engine) as session:
        orders_db = session.exec(select(OrderRecords).where(OrderRecords.customer_id == customer.id).order_by(OrderRecords.order_date.desc())).all()
        
        final_results = []
        for order in orders_db:
            order_schema = OrderRecordsRead.model_validate(order)
            items_with_product = session.exec(
                select(OrderItem, Product.name)
                .join(Product, Product.id == OrderItem.product_id)
                .where(OrderItem.orderrecords_id == order.id)
            ).all()
            
            order_items_data = []
            for item, p_name in items_with_product:
                i_dict = item.model_dump()
                i_dict['product_name'] = p_name
                order_items_data.append(i_dict)
            
            order_schema.items = order_items_data
            final_results.append(order_schema)
            
        return final_results
    
# -------------------------------------------------------------------------------------------------------------------------------------------------
# --- Retailer Auth Endpoints ---
# -------------------------------------------------------------------------------------------------------------------------------------------------

@app.post("/signup/retailer", response_model=RetailerRead, status_code=status.HTTP_201_CREATED, tags=["Retailer Auth"])
async def signup_retailer(
    retailer: RetailerCreate,
    background_tasks: BackgroundTasks # <--- NEW: Required for sending email
):
    
    exists = await run_in_threadpool(get_retailer_by_email, retailer.mail)
    if exists:
        raise HTTPException(status_code=400, detail="Email Already Registered")

    hashed_password = hash_password(retailer.password)
    
    new_retailer = await run_in_threadpool(
        add_retailer,
        name=retailer.name,
        mail=retailer.mail,
        hashed_password=hashed_password,
        business_name=retailer.business_name,
        address=retailer.address,
        city=retailer.city,
        state=retailer.state,
        pincode=retailer.pincode,
        phone_number=retailer.phone_number,
        tax_id=retailer.tax_id,
        lat=retailer.lat,
        lon=retailer.lon
    )

    if not new_retailer:
        raise HTTPException(status_code=500, detail="Failed to create Retailer.")
    
    # --- NEW: Send Verification OTP ---
    otp = generate_otp()
    await run_in_threadpool(save_verification_otp, retailer.mail, otp)
    await send_verification_email(retailer.mail, otp, background_tasks)
    # ----------------------------------
    
    return new_retailer

@app.post("/login/retailer", response_model=Token, tags=["Retailer Auth"])
async def login_retailer(
    req: LoginRequest
):
    
    retailer = await run_in_threadpool(get_retailer_by_email, req.mail)
    if not retailer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    # --- NEW: Verify if account is active ---
    if not retailer.is_verified:
        raise HTTPException(status_code=403, detail="Account not verified. Please verify your email.")
    # ----------------------------------------

    if not verify_password(req.password, retailer.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    # Create and return JWT token
    access_token = create_access_token(data={"sub": retailer.mail, "role": "retailer"})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/retailer/me", response_model=RetailerRead, tags=["Retailer Auth"])
async def get_me(retailer: Retailer = Depends(get_current_retailer)):
    return retailer


# -------------------------------------------------------------------------------------------------------------------------------------------------
# --- Wholesaler Auth Endpoints ---
# -------------------------------------------------------------------------------------------------------------------------------------------------

@app.post("/signup/wholesaler", response_model=WholesalerRead, status_code=status.HTTP_201_CREATED, tags=["Wholesaler Auth"])
async def signup_wholesaler(
    wholesaler: WholesalerCreate,
    background_tasks: BackgroundTasks # <--- NEW: Required for sending email
):
    
    exists = await run_in_threadpool(get_wholesaler_by_email, wholesaler.mail)
    if exists:
        raise HTTPException(status_code=400, detail="Email Already Registered")

    hashed_password = hash_password(wholesaler.password)
    
    new_wholesaler = await run_in_threadpool(
        add_wholesaler,
        name=wholesaler.name,
        mail=wholesaler.mail,
        hashed_password=hashed_password,
        business_name=wholesaler.business_name,
        address=wholesaler.address,
        city=wholesaler.city,
        state=wholesaler.state,
        pincode=wholesaler.pincode,
        phone_number=wholesaler.phone_number,
        tax_id=wholesaler.tax_id,
        lat=wholesaler.lat,
        lon=wholesaler.lon
    )

    if not new_wholesaler:
        raise HTTPException(status_code=500, detail="Failed to create Wholesaler.")
    
    # --- NEW: Send Verification OTP ---
    otp = generate_otp()
    await run_in_threadpool(save_verification_otp, wholesaler.mail, otp)
    await send_verification_email(wholesaler.mail, otp, background_tasks)
    # ----------------------------------
    
    return new_wholesaler

@app.post("/login/wholesaler", response_model=Token, tags=["Wholesaler Auth"])
async def login_wholesaler(
    req: LoginRequest
):
    
    wholesaler = await run_in_threadpool(get_wholesaler_by_email, req.mail)
    if not wholesaler:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    # --- NEW: Verify if account is active ---
    if not wholesaler.is_verified:
        raise HTTPException(status_code=403, detail="Account not verified. Please verify your email.")
    # ----------------------------------------

    if not verify_password(req.password, wholesaler.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    # Create and return JWT token
    access_token = create_access_token(data={"sub": wholesaler.mail, "role": "wholesaler"})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/wholesaler/me", response_model=WholesalerRead, tags=["Wholesaler Auth"])
async def get_me(wholesaler: Wholesaler = Depends(get_current_wholesaler)):
    return wholesaler


# -------------------------------------------------------------------------------------------------------------------------------------------------
# Account Verification Endpoints 
# -------------------------------------------------------------------------------------------------------------------------------------------------

@app.post("/auth/verify-account", status_code=status.HTTP_200_OK, tags=["Auth"])
async def verify_account_endpoint(req: AccountVerificationRequest):
    
    # 1. Convert to Dict (Safest way to read data)
    try:
        data = req.model_dump() # Pydantic v2
    except AttributeError:
        data = req.dict()       # Pydantic v1 fallback
        
    email = data.get("email")
    otp = data.get("otp")
    role = data.get("role") # Safely get role (returns None if missing)

    # 2. Verify OTP
    success = await run_in_threadpool(verify_user_account, email, otp)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or Expired OTP")

    # 3. Determine Final Role
    final_role = role
    
    # Fallback: If frontend didn't send role, check DB
    if not final_role:
        if await run_in_threadpool(get_customer_by_email, email): final_role = "customer"
        elif await run_in_threadpool(get_retailer_by_email, email): final_role = "retailer"
        elif await run_in_threadpool(get_wholesaler_by_email, email): final_role = "wholesaler"

    if not final_role:
        raise HTTPException(status_code=404, detail="User verified but role not found.")

    # 4. Generate Token
    access_token = create_access_token(data={"sub": email, "role": final_role})
        
    return {
        "message": "Verified",
        "access_token": access_token,
        "token_type": "bearer",
        "role": final_role
    }


@app.post("/auth/resend-verification", tags=["Auth"])
async def resend_verification(email: str, background_tasks: BackgroundTasks):
    # Check if user exists
    customer = await run_in_threadpool(get_customer_by_email, email)
    retailer = await run_in_threadpool(get_retailer_by_email, email)
    wholesaler = await run_in_threadpool(get_wholesaler_by_email, email)
    
    user = customer or retailer or wholesaler
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_verified:
        return {"message": "Account already verified"}
        
    otp = generate_otp()
    await run_in_threadpool(save_verification_otp, email, otp)
    await send_verification_email(email, otp, background_tasks)
    
    return {"message": "Verification OTP Resent."}


# -------------------------------------------------------------------------------------------------------------------------------------------------
# --- Social Login Endpoints ---
# -------------------------------------------------------------------------------------------------------------------------------------------------


# Google Auth Endpoints
@app.get("/login/google", tags=["Social Auth"])
async def login_google(request: Request):
    # This creates the redirect URL: http://127.0.0.1:8000/auth/google
    redirect_uri = request.url_for('auth_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

# FIND AND REPLACE THE ENTIRE 'auth_google' FUNCTION WITH THIS:

@app.get("/auth/google", tags=["Social Auth"])
async def auth_google(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo') or await oauth.google.userinfo(token=token)
        email = user_info.get('email')
        name = user_info.get('name') or email.split('@')[0] 

        role = "customer"
        redirect_page = "Customer.html"
        
        # Check Retailer
        retailer = await run_in_threadpool(get_retailer_by_email, email)
        if retailer:
            role = "retailer"
            redirect_page = "Retailer.html"
            if not retailer.is_verified:
                with Session(engine) as s:
                    r = s.get(Retailer, retailer.id)
                    r.is_verified = True
                    s.add(r); s.commit()
        
        # Check Wholesaler
        elif await run_in_threadpool(get_wholesaler_by_email, email):
            role = "wholesaler"
            redirect_page = "Wholesaler.html"
        
        # Default to Customer
        else:
            customer = await run_in_threadpool(get_customer_by_email, mail=email)
            if not customer:
                random_pass = hash_password(email + datetime.utcnow().isoformat())
                customer = await run_in_threadpool(add_customer, name=name, mail=email, hashed_password=random_pass)
            
            if not customer.is_verified:
                 with Session(engine) as s:
                    c = s.get(Customer, customer.id)
                    c.is_verified = True
                    s.add(c); s.commit()
        
        access_token = create_access_token(data={"sub": email, "role": role})
        return RedirectResponse(url=f"/{redirect_page}?token={access_token}")
             
    except Exception as e:
        print(f"GOOGLE AUTH ERROR: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Google Login Failed: {str(e)}")
    
# -------------------------------------------------------------------------------------------------------------------------------------------------
# --- Product Endpoints ---
# -------------------------------------------------------------------------------------------------------------------------------------------------

# 1. GET ALL PRODUCTS
# Matches requests to "/products" (e.g., from dashboard.html)
@app.get("/products", response_model=List[ProductRead], tags=["Products"])
def get_all_products(
    q: Optional[str] = None,
    category: Optional[str] = None, 
    min_price: Optional[float] = None, 
    max_price: Optional[float] = None,
    sort_by: Optional[str] = "newest"
):
    with Session(engine) as session:
        query = select(Product)
        
        # --- FIX: HARDCODED CATEGORY MAPPING ---
        # Matches the IDs used in retailer-add-product.html
        cat_map = {
            "electronics": 1,
            "groceries": 2,
            "fashion": 3,
            "books": 5,
            "sports": 8, # Matches 'Sports' in your HTML
            "home": 7    # Matches 'Home' in your HTML
            # Add others if needed
        }

        # Search Logic
        if q:
            search_term = f"%{q}%"
            query = query.where(
                or_(
                    col(Product.name).ilike(search_term),
                    col(Product.description).ilike(search_term)
                )
            )
            
        # Category Logic
        if category and category.lower() != "all":
            if category.isdigit():
                query = query.where(Product.category_id == int(category))
            else:
                # Check our manual map instead of the empty DB table
                cat_id = cat_map.get(category.lower())
                if cat_id:
                    query = query.where(Product.category_id == cat_id)
            
        # Filtering & Sorting
        if min_price is not None:
            query = query.where(Product.price >= min_price)
        if max_price is not None:
            query = query.where(Product.price <= max_price)
            
        if sort_by == "price_low":
            query = query.order_by(Product.price.asc())
        elif sort_by == "price_high":
            query = query.order_by(Product.price.desc())
        else:
            query = query.order_by(Product.id.desc())
            
        return session.exec(query).all()

# 2. GET SINGLE PRODUCT
# Matches requests to "/products/100" (e.g., from product-details.html)
@app.get("/products/{product_id}", response_model=ProductRead, tags=["Products"])
async def get_product_detail(product_id: int):
    with Session(engine) as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

# 3. ADD PRODUCT
@app.post("/products/add/", response_model=ProductRead, status_code=status.HTTP_201_CREATED, tags=["Products"])
async def create_product_endpoint(
    name: str = Form(...),
    price: float = Form(...),
    stock: int = Form(...),
    description: str = Form(None),
    category_id: int = Form(...),
    image: UploadFile = File(None), # Optional file upload
    current_retailer: Retailer = Depends(get_current_retailer)
):
    # 1. Create the product in DB first (to get the ID)
    # We set a temporary image_url
    new_product = await run_in_threadpool(
        add_product,
        name, price, stock, current_retailer.id,
        description, category_id, "" 
    )
    
    if not new_product:
        raise HTTPException(status_code=500, detail="Failed to create product.")

    # 2. Handle Image Upload
    if image:
        # Create file path: product_images/{id}.jpg
        # We preserve the original extension or default to .jpg
        file_extension = image.filename.split(".")[-1]
        file_name = f"{new_product.id}.{file_extension}"
        file_path = os.path.join(product_images_dir, file_name)
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            
            # Update DB with the new path
            # Note: We use forward slashes for URL compatibility
            relative_path = f"product_images/{file_name}"
            
            # We need a small helper to update just the image_url
            # For now, we can re-use update_product_details or do it manually here
            with Session(engine) as session:
                p = session.get(Product, new_product.id)
                p.image_url = relative_path
                session.add(p)
                session.commit()
                session.refresh(p)
                new_product = p # Update return object
                
        except Exception as e:
            print(f"Error saving image: {e}")
            # We don't fail the request, just the image upload part
            pass
    else:
        # Set default if no image uploaded
        with Session(engine) as session:
            p = session.get(Product, new_product.id)
            p.image_url = "product_images/default.png"
            session.add(p)
            session.commit()
            session.refresh(p)
            new_product = p

    return new_product


# 1. DELETE PRODUCT
@app.delete("/retailer/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Retailer Workflow"])
async def delete_product(
    product_id: int,
    current_retailer: Retailer = Depends(get_current_retailer)
):
    with Session(engine) as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if product.retailer_id != current_retailer.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this product")
        
        session.delete(product)
        session.commit()
        return None

# 2. GET CUSTOMER PURCHASE HISTORY (For this retailer)
@app.get("/retailer/customer-history", tags=["Retailer Workflow"])
async def get_customer_history(current_retailer: Retailer = Depends(get_current_retailer)):
    with Session(engine) as session:
        # Get all orders containing this retailer's products
        # We join OrderItem -> Product -> OrderRecords -> Customer
        statement = select(OrderRecords, Customer, Product, OrderItem)\
            .join(OrderItem, OrderItem.orderrecords_id == OrderRecords.id)\
            .join(Product, Product.id == OrderItem.product_id)\
            .join(Customer, Customer.id == OrderRecords.customer_id)\
            .where(Product.retailer_id == current_retailer.id)\
            .order_by(OrderRecords.order_date.desc())
            
        results = session.exec(statement).all()
        
        # Format data for frontend
        history = []
        for order, customer, product, item in results:
            history.append({
                "order_id": order.id,
                "date": order.order_date,
                "customer_name": customer.name,
                "customer_email": customer.mail,
                "product_name": product.name,
                "quantity": item.quantity,
                "total_paid": item.price_at_purchase * item.quantity
            })
        return history

# 3. B2B: GET WHOLESALE PRODUCTS (Mock logic: Wholesaler items are just products with a flag or separate table)
# For simplicity, we'll return a mock list or query a specific "Wholesale" category if you have one.
# Let's assume we create a fake list for now to demonstrate the UI.
@app.get("/retailer/wholesale-market", tags=["Retailer Workflow"])
async def get_wholesale_market(current_retailer: Retailer = Depends(get_current_retailer)):
    # In a real app, you'd query the Product table where `is_wholesale=True`
    # Here we return a static list for demonstration
    return [
        {"id": 901, "name": "Bulk Rice (50kg)", "price": 2500, "min_qty": 10, "supplier": "Global Grains"},
        {"id": 902, "name": "Cotton T-Shirts (Pack of 100)", "price": 15000, "min_qty": 1, "supplier": "Textile Hub"},
        {"id": 903, "name": "Smartphone Batch (10 units)", "price": 120000, "min_qty": 1, "supplier": "Tech Wholesalers"},
        {"id": 904, "name": "Cooking Oil (20L)", "price": 3000, "min_qty": 5, "supplier": "Pure Oils Ltd"}
    ]

# 4. B2B: PLACE WHOLESALE ORDER
@app.post("/retailer/wholesale-order", tags=["Retailer Workflow"])
async def place_wholesale_order(
    item_id: int, 
    quantity: int, 
    current_retailer: Retailer = Depends(get_current_retailer)
):
    # In a real app, this would create a WholesaleOrder record
    # For now, we just simulate success
    return {"message": f"Order placed for Item #{item_id} (Qty: {quantity}). Supplier notified."}


# -------------------------------------------------------------------------------------------------------------------------------------------------
# --- Cart and Checkout Endpoints ---
# -------------------------------------------------------------------------------------------------------------------------------------------------

# FIX: Use Optional[ShoppingCartItemRead] because removal returns None
@app.post("/cart/add", response_model=Optional[ShoppingCartItemRead], tags=["Cart & Checkout"])
async def add_to_cart(
    item: ShoppingCartItemCreate, 
    customer: Customer = Depends(get_current_customer) # This endpoint is now secured
):
    
    cart = await run_in_threadpool(get_cart_by_customer_id, customer_id=customer.id)
    if not cart:
        raise HTTPException(status_code=404, detail="Customer cart not found")
    
    try:
        new_item = await run_in_threadpool(
            add_item_to_cart,
            product_id=item.product_id,
            quantity=item.quantity,
            cart_id=cart.id
        )
        return new_item
    except HTTPException as e:
        raise e # Re-raise stock or not-found errors
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cart", response_model=CartRead, tags=["Cart & Checkout"])
async def get_customer_cart(
    customer: Customer = Depends(get_current_customer) # This endpoint is now secured
):
    
    cart = await run_in_threadpool(get_cart_by_customer_id, customer_id=customer.id)
    if not cart:
        raise HTTPException(status_code=404, detail="Customer cart not found")
        
    detailed_items = await run_in_threadpool(get_detailed_cart_items, cart_id=cart.id)
    
    total_size = sum(item['quantity'] for item in detailed_items)
    
    return {"items": detailed_items, "total_size": total_size}


@app.post("/order/checkout", response_model=OrderRecordsRead, tags=["Cart & Checkout"])
async def checkout(
    order_details: OrderCreate, 
    customer: Customer = Depends(get_current_customer) # This endpoint is now secured
):
    # 1. Validations before hitting DB logic
    if not order_details.shipping_address or not order_details.shipping_city or not order_details.shipping_pincode:
        raise HTTPException(status_code=400, detail="Shipping address details are incomplete.")
        
    try:
        # 2. Run the transaction
        new_order = await run_in_threadpool(
            process_checkout,
            customer=customer,
            order_details=order_details
        )
        
        if not new_order:
             raise HTTPException(status_code=400, detail="Checkout failed. Cart might be empty.")

        return new_order
        
    except HTTPException as e:
        raise e # Re-raise stock or empty cart errors
    except Exception as e:
        # Generic error for other potential failures
        print(f"Checkout Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred during checkout: {str(e)}")


# -------------------------------------------------------------------------------------------------------------------------------------------------
# --- Retailer Workflow Endpoints ---
# -------------------------------------------------------------------------------------------------------------------------------------------------

@app.get("/retailer/my-products", response_model=List[ProductRead], tags=["Retailer Workflow"])
async def get_my_products(current_retailer: Retailer = Depends(get_current_retailer)):
    
    products = await run_in_threadpool(get_products_by_retailer, retailer_id=current_retailer.id)
    return products


@app.get("/retailers/locations", tags=["Retailer Workflow"])
def get_retailer_locations():
    """Returns a list of retailers with their coordinates for the map."""
    with Session(engine) as session:
        # Fetch retailers who have lat/lon set
        statement = select(Retailer).where(Retailer.lat != None).where(Retailer.lon != None)
        retailers = session.exec(statement).all()
        
        map_data = []
        for r in retailers:
            map_data.append({
                "id": r.id,
                "name": r.business_name,
                "lat": r.lat,
                "lon": r.lon,
                "address": r.address
            })
        return map_data


@app.put("/retailer/products/{product_id}", response_model=ProductRead, tags=["Retailer Workflow"])
async def update_product(
    product_id: int, 
    update_data: ProductUpdate,
    current_retailer: Retailer = Depends(get_current_retailer)
):
    
    product = await run_in_threadpool(get_product_by_id, product_id=product_id)
    
    # Check if product exists and belongs to the retailer
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.retailer_id != current_retailer.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this product")
        
    updated_product = await run_in_threadpool(update_product_details, product=product, update_data=update_data)
    return updated_product

@app.get("/retailer/orders", response_model=List[OrderRecordsRead], tags=["Retailer Workflow"])
async def get_my_orders(current_retailer: Retailer = Depends(get_current_retailer)):
    
    orders = await run_in_threadpool(get_orders_by_retailer, retailer_id=current_retailer.id)
    # Note: This returns orders without the 'items' list populated.
    return orders

@app.put("/retailer/orders/{order_id}/status", response_model=OrderRecordsRead, tags=["Retailer Workflow"])
async def update_order(
    order_id: int,
    status_update: OrderStatusUpdate,
    current_retailer: Retailer = Depends(get_current_retailer)
):
    
    # First, verify this order actually belongs to the retailer
    retailer_orders = await run_in_threadpool(get_orders_by_retailer, retailer_id=current_retailer.id)
    order_ids = [order.id for order in retailer_orders]
    
    if order_id not in order_ids:
        raise HTTPException(status_code=403, detail="Not authorized to update this order")
        
    order = await run_in_threadpool(get_order_by_id, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    updated_order = await run_in_threadpool(update_order_status, order=order, status_update=status_update)
    return updated_order


# -------------------------------------------------------------------------------------------------------------------------------------------------

# --- Wholesaler Workflow ---

@app.get("/wholesaler/orders", response_model=List[WholesaleOrder], tags=["Wholesaler Workflow"])
async def get_wholesale_orders(current_wholesaler: Wholesaler = Depends(get_current_wholesaler)):
    with Session(engine) as session:
        statement = select(WholesaleOrder).where(WholesaleOrder.wholesaler_id == current_wholesaler.id)
        orders = session.exec(statement).all()
        return orders

# In main.py

# ... inside main.py ...

# REPLACE the existing update_wholesale_order_status with this:
# FIND AND REPLACE THE ENTIRE 'update_wholesale_order_status' FUNCTION WITH THIS:

@app.put("/wholesaler/orders/{order_id}/status", response_model=WholesaleOrder, tags=["Wholesaler Workflow"])
def update_wholesale_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    current_wholesaler: Wholesaler = Depends(get_current_wholesaler)
):
    with Session(engine) as session:
        order = session.get(WholesaleOrder, order_id)
        if not order: raise HTTPException(status_code=404, detail="Order not found")
        if order.wholesaler_id != current_wholesaler.id: raise HTTPException(status_code=403, detail="Not authorized")
            
        # --- ADDED STOCK UPDATE ---
        if status_update.status in ["Shipped", "Approved"] and order.status not in ["Shipped", "Approved"]:
            items = session.exec(select(WholesaleOrderItem).where(WholesaleOrderItem.wholesale_order_id == order.id)).all()
            for item in items:
                product = session.get(Product, item.product_id)
                if product:
                    product.stock += item.quantity
                    session.add(product)
        # --------------------------

        order.status = status_update.status
        session.add(order)
        session.commit()
        session.refresh(order)
        return order

# -------------------------------------------------------------------------------------------------------------------------------------------------

# Password Forgot Endpoint
@app.post("/auth/forgot-password" , status_code=status.HTTP_200_OK , tags=["Auth"])
async def forgot_password(request: ForgotPasswordRequest , background_tasks: BackgroundTasks):

    email = request.email

    customer = await run_in_threadpool(get_customer_by_email, email)
    retailer = await run_in_threadpool(get_retailer_by_email, email)
    wholesaler = await run_in_threadpool(get_wholesaler_by_email, email)

    if not (customer or retailer or wholesaler):
        raise HTTPException(status_code=404 , detail="User with this mail does not exist")
    
    otp = generate_otp()
    expiration = datetime.utcnow() + timedelta(minutes=10) # OTP is valid for 10min

    with Session(engine) as session:
        
        existing = session.exec(select(PasswordReset).where(PasswordReset.email == email)).all()

        # Deleting the record if exists a already OTP request
        for record in existing:
            session.delete(record)

        # Making a new one
        reset_entry = PasswordReset(email=email, otp=otp, expires_at=expiration)
        session.add(reset_entry)
        session.commit()

    await send_otp_email(email , otp, background_tasks)

    return {"message": "OTP sent to your email."}


# Password Reset Endpoint
@app.post("/auth/reset-password", status_code=status.HTTP_200_OK, tags=['Auth'])
def reset_password(request: ResetPasswordRequest): # Removed async
    with Session(engine) as session:
        # 1. Validate OTP
        statement = select(PasswordReset).where(
            (PasswordReset.email == request.email) &
            (PasswordReset.otp == request.otp) 
        )
        reset_record = session.exec(statement).first()

        if not reset_record:
            raise HTTPException(status_code=400, detail="Invalid OTP.")
        
        if reset_record.expires_at < datetime.utcnow():
            session.delete(reset_record)
            session.commit()
            raise HTTPException(status_code=400, detail="OTP has expired.")
        
        # 2. Update Password (Hash it once)
        new_hashed_password = hash_password(request.new_password)
        
        user_found = False

        # Check Customer (Always check)
        customer = session.exec(select(Customer).where(Customer.mail == request.email)).first()
        if customer:
            customer.hashed_password = new_hashed_password
            session.add(customer)
            user_found = True

        # Check Retailer (Always check - REMOVED "if not user_found")
        retailer = session.exec(select(Retailer).where(Retailer.mail == request.email)).first()
        if retailer:
            retailer.hashed_password = new_hashed_password
            session.add(retailer)
            user_found = True

        # Check Wholesaler (Always check - REMOVED "if not user_found")
        wholesaler = session.exec(select(Wholesaler).where(Wholesaler.mail == request.email)).first()
        if wholesaler:
            wholesaler.hashed_password = new_hashed_password
            session.add(wholesaler)
            user_found = True
        
        if not user_found:
            raise HTTPException(status_code=404, detail="User account not found.")

        # 3. Delete the OTP
        session.delete(reset_record)
        session.commit()
        
        return {"message": "Password updated successfully. You can now login."}
    

# Verifying OTP
@app.post("/auth/verify-otp-only", status_code=status.HTTP_200_OK, tags=["Auth"])
async def verify_otp_only(request: OTPVerifyRequest):
    """
    Checks if OTP is valid without resetting password or deleting the OTP.
    Used for the frontend 'Next' button.
    """
    with Session(engine) as session:
        statement = select(PasswordReset).where(
            (PasswordReset.email == request.email) & 
            (PasswordReset.otp == request.otp)
        )
        reset_record = session.exec(statement).first()

        if not reset_record:
            raise HTTPException(status_code=400, detail="Invalid OTP Code.")

        if reset_record.expires_at < datetime.utcnow():
            session.delete(reset_record) # Cleanup expired
            session.commit()
            raise HTTPException(status_code=400, detail="OTP has expired.")
            
        return {"message": "OTP is valid."}


# ----------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------------------------------------------------------

# Static File Mounting - USING ABSOLUTE PATHS FOR RELIABILITY
import os 

# 1. Get base directory of this file (backend/app)
base_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Calculate absolute paths to data and frontend
product_images_dir = os.path.join(base_dir, "../data/product_images")
frontend_dir = os.path.join(base_dir, "../../frontend")

# 3. Ensure directories exist (Optional safety check)
if not os.path.exists(product_images_dir):
    print(f"WARNING: Product images directory not found at {product_images_dir}")
    # Create it to prevent 500 errors, though images will be 404
    os.makedirs(product_images_dir, exist_ok=True)

# 4. Mount Product Images BEFORE frontend
# Maps http://localhost:8000/product_images/... -> backend/data/product_images/...
app.mount("/product_images", StaticFiles(directory=product_images_dir), name="product_images")
# ... existing product_images_dir logic ...
profile_pictures_dir = os.path.join(base_dir, "../data/profile_pictures") # <--- Define path

# ... existing product_images mount ...
app.mount("/product_images", StaticFiles(directory=product_images_dir), name="product_images")

# --- ADD THIS LINE ---
app.mount("/profile_pictures", StaticFiles(directory=profile_pictures_dir), name="profile_pictures")

# 5. Mount Frontend LAST (Catch-all)
# Maps http://localhost:8000/... -> frontend/...
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")