# App

# Importing FastAPI
from fastapi import FastAPI , HTTPException , status, Depends, Form , BackgroundTasks
from typing import List, Annotated

# For file management
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
    

    engine
)

# Importing the SQLModel classes
from db_models import (Customer, 
                       Product, 
                       ShoppingCart,
                        ShoppingCartItem, 
                        Retailer,
                        Wholesaler ,
                        PasswordReset, 
                        OrderRecords,
                        Category)

# Importing the Schemas
from schemas import *

# --------------------------------------------------------------------------------------------------------------------------------------------


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
app.mount("/static" , StaticFiles(directory="../data") , name="static")

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
async def signup_customer(customer : CustomerCreate):

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
@app.get("/customer/orders", response_model=List[OrderRecordsRead], tags=["Cart & Checkout"])
async def get_my_orders(customer: Customer = Depends(get_current_customer)):
    with Session(engine) as session:
        statement = select(OrderRecords).where(OrderRecords.customer_id == customer.id)
        orders = session.exec(statement).all()
        return orders


# -------------------------------------------------------------------------------------------------------------------------------------------------
# --- Retailer Auth Endpoints ---
# -------------------------------------------------------------------------------------------------------------------------------------------------

@app.post("/signup/retailer", response_model=RetailerRead, status_code=status.HTTP_201_CREATED, tags=["Retailer Auth"])
async def signup_retailer(retailer: RetailerCreate):
    
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
    
    return new_retailer

@app.post("/login/retailer", response_model=Token, tags=["Retailer Auth"])
async def login_retailer(
    req: LoginRequest
):
    
    retailer = await run_in_threadpool(get_retailer_by_email, req.mail)
    if not retailer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

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
async def signup_wholesaler(wholesaler: WholesalerCreate):
    
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
    
    return new_wholesaler

@app.post("/login/wholesaler", response_model=Token, tags=["Wholesaler Auth"])
async def login_wholesaler(
    req: LoginRequest
):
    
    wholesaler = await run_in_threadpool(get_wholesaler_by_email, req.mail)
    if not wholesaler:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    if not verify_password(req.password, wholesaler.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    # Create and return JWT token
    access_token = create_access_token(data={"sub": wholesaler.mail, "role": "wholesaler"})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/wholesaler/me", response_model=WholesalerRead, tags=["Wholesaler Auth"])
async def get_me(wholesaler: Wholesaler = Depends(get_current_wholesaler)):
    return wholesaler


# -------------------------------------------------------------------------------------------------------------------------------------------------
# --- Social Login Endpoints ---
# -------------------------------------------------------------------------------------------------------------------------------------------------


# Google Auth Endpoints
@app.get("/login/google", tags=["Social Auth"])
async def login_google(request: Request):
    # This creates the redirect URL: http://127.0.0.1:8000/auth/google
    redirect_uri = request.url_for('auth_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google", tags=["Social Auth"])
async def auth_google(request: Request):
    try:
        # 1. Exchange the auth code for a token
        token = await oauth.google.authorize_access_token(request)
        
        # 2. Get the user's info from Google
        user_info = token.get('userinfo')
        if not user_info:
            user_info = await oauth.google.userinfo(token=token)
            
        email = user_info.get('email')
        name = user_info.get('name')
        
        # 3. Check if this customer already exists in our DB
        customer = await run_in_threadpool(get_customer_by_email, mail=email)
        
        if not customer:
            # 4. If not, create a new account automatically
            # We generate a random secure password since they login via Google
            random_pass = hash_password(email + datetime.utcnow().isoformat())
            customer = await run_in_threadpool(
                add_customer,
                name=name,
                mail=email,
                hashed_password=random_pass
            )
            
        # 5. Generate a JWT token for our app
        access_token = create_access_token(data={"sub": customer.mail, "role": "customer"})
        
        # 6. Redirect to the frontend Customer page, passing the token in the URL
        return RedirectResponse(url=f"/Customer.html?token={access_token}")
        
    except Exception as e:
        # If something goes wrong, show the error
        raise HTTPException(status_code=400, detail=f"Google Login Failed: {str(e)}")


# -------------------------------------------------------------------------------------------------------------------------------------------------
# --- Product Endpoints ---
# -------------------------------------------------------------------------------------------------------------------------------------------------

# Product Details Endpoint - GET ---> Accepts 
@app.get("/products/info/{product_id}" , response_model=ProductRead, tags=["Products"])
async def get_product(product_id: int):
    def _get():
        with Session(engine) as session:
            return session.exec(select(Product).where(Product.id == product_id)).first()

    prod = await run_in_threadpool(_get)

    # If Product ID does not exist
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return prod


# Getting all products
@app.get("/products/all", response_model=List[ProductRead], tags=["Products"])
async def get_all_products(
    q: str = None,                # Search query (e.g., "coffee")
    category: str = None, 
    min_price: float = None, 
    max_price: float = None,
    sort_by: str = "newest"       # Sorting: "newest", "price_low", "price_high"
):
    with Session(engine) as session:
        query = select(Product)
        
        # 1. Text Search (Name OR Description)
        if q:
            search_term = f"%{q}%"
            # Use col() to enable case-insensitive 'like' or standard 'contains'
            query = query.where(
                or_(
                    col(Product.name).like(search_term),
                    col(Product.description).like(search_term)
                )
            )
            
        # 2. Filter by Category Name
        if category and category.lower() != "all":
            query = query.join(Category).where(Category.name == category)
            
        # 3. Filter by Price
        if min_price is not None:
            query = query.where(Product.price >= min_price)
        if max_price is not None:
            query = query.where(Product.price <= max_price)
            
        # 4. Sorting
        if sort_by == "price_low":
            query = query.order_by(Product.price.asc())
        elif sort_by == "price_high":
            query = query.order_by(Product.price.desc())
        else: # "newest" (Default)
            # Assuming IDs increment with time; ideally use a created_at field
            query = query.order_by(Product.id.desc())
            
        products = session.exec(query).all()
        return products


# Adding Product Endpoint - POST ---> Accepts JSON Body as response
@app.post("/products/add/" , response_model=ProductRead , status_code=status.HTTP_201_CREATED, tags=["Products"])
async def create_product_endpoint(
    product : ProductCreate, 
    current_retailer: Retailer = Depends(get_current_retailer) # This endpoint is now secured
):
    
    # retailer_id is now taken from the authenticated user, not the request body
    new_product = await run_in_threadpool(
        add_product,
        product.name,
        product.price,
        product.stock,
        current_retailer.id, # Use the logged-in retailer's ID
        product.description,
        product.category_id,
        product.image_url
    )

    if not new_product:
        raise HTTPException(status_code=500 , detail="Failed to create product. Try again! Oops lol")
    
    return new_product


# -------------------------------------------------------------------------------------------------------------------------------------------------
# --- Cart and Checkout Endpoints ---
# -------------------------------------------------------------------------------------------------------------------------------------------------

@app.post("/cart/add", response_model=ShoppingCartItemRead, tags=["Cart & Checkout"])
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
    
    try:
        new_order = await run_in_threadpool(
            process_checkout,
            customer=customer,
            order_details=order_details
        )
        
        # Note: We need to load the 'items' relationship manually
        # For now, we'll just return the main order record.
        # Populating the 'items' in OrderRecordsRead is an advanced step.
        return new_order
        
    except HTTPException as e:
        raise e # Re-raise stock or empty cart errors
    except Exception as e:
        # Generic error for other potential failures
        raise HTTPException(status_code=500, detail=f"An error occurred during checkout: {str(e)}")


# -------------------------------------------------------------------------------------------------------------------------------------------------
# --- Retailer Workflow Endpoints ---
# -------------------------------------------------------------------------------------------------------------------------------------------------

@app.get("/retailer/my-products", response_model=List[ProductRead], tags=["Retailer Workflow"])
async def get_my_products(current_retailer: Retailer = Depends(get_current_retailer)):
    
    products = await run_in_threadpool(get_products_by_retailer, retailer_id=current_retailer.id)
    return products

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
@app.post("/auth/reset-password" , status_code=status.HTTP_200_OK , tags=['Auth'])
async def reset_password(request: ResetPasswordRequest):

    # Checking if request has been made or not
    with Session(engine) as session:

        statement = select(PasswordReset).where(
            (PasswordReset.email == request.email) &
            (PasswordReset.otp == request.otp) 
        )

        reset_record  = session.exec(statement).first()

        if not reset_record:
            raise HTTPException(status_code=400, detail="Invalid OTP.")
        
        # If OTP expired
        if reset_record.expires_at < datetime.utcnow():
            session.delete(reset_record) # 
            session.commit()
            raise HTTPException(status_code=400, detail="OTP has expired.")
        

        # Updating the password
        new_hashed_password = hash_password(request.new_password)
        
        # Finding the user
        user_found = False

        # Checking for customer
        customer = session.exec(select(Customer).where(Customer.mail == request.email)).first()
        if customer:
            customer.hashed_password = new_hashed_password
            session.add(customer)
            user_found = True

        # Checking for Retailer
        if not user_found:
            retailer = session.exec(select(Retailer).where(Retailer.mail == request.email)).first()
            if retailer:
                retailer.hashed_password = new_hashed_password
                session.add(retailer)
                user_found = True

        # Checking for Wholesaler
        if not user_found:
            wholesaler = session.exec(select(Wholesaler).where(Wholesaler.mail == request.email)).first()
            if wholesaler:
                wholesaler.hashed_password = new_hashed_password
                session.add(wholesaler)
                user_found = True
        
        if not user_found:
            raise HTTPException(status_code=404, detail="User account not found.")

        # 3. Delete the OTP so it can't be used again
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

# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------------------------------------------------------

# Mount your frontend
app.mount("/", StaticFiles(directory="../../frontend", html=True), name="frontend")