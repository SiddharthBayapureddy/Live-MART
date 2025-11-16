# App

# Importing FastAPI
from fastapi import FastAPI , HTTPException , status, Depends, Form
from typing import List, Annotated

# For file management
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session, select
from contextlib import asynccontextmanager

from fastapi.concurrency import run_in_threadpool

from auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    get_current_retailer,
    get_current_customer,
    get_current_wholesaler,
    customer_oauth2_scheme, # Import the new schemes
    retailer_oauth2_scheme,
    wholesaler_oauth2_scheme
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

    engine
)

# Importing the SQLModel classes
from db_models import Customer, Product, ShoppingCart, ShoppingCartItem, Retailer, Wholesaler

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

# This tells the /docs UI how to set up the "Authorize" button
security_schemes = {
    "Customer": customer_oauth2_scheme,
    "Retailer": retailer_oauth2_scheme,
    "Wholesaler": wholesaler_oauth2_scheme,
}
app = FastAPI(
    title="Live MART" , 
    lifespan=lifespan,
    swagger_ui_parameters={"securitySchemes": security_schemes}
)


# Mounting the app to folder at "../data"
app.mount("/static" , StaticFiles(directory="../data") , name="static")

# Creating endpoints

# Root 
@app.get("/")
def root():
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

# Login Endpoint - POST ---> Accepts Form Data
@app.post("/login/customer", response_model=Token, tags=["Customer Auth"])
async def login_customer(
    username: Annotated[str, Form()], 
    password: Annotated[str, Form()]
):

    # Checking if customer exists
    customer = await run_in_threadpool(get_customer_by_email , username)

    if not customer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail="Invalid Credentials: Mail not found")
    

    # Checking password
    # Password incorrect
    if not verify_password(password, customer.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail="Invalid Credentials: Password not found")
    
    # Create and return JWT token
    access_token = create_access_token(data={"sub": customer.mail, "role": "customer"})
    return {"access_token": access_token, "token_type": "bearer"}


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
    username: Annotated[str, Form()], 
    password: Annotated[str, Form()]
):
    
    retailer = await run_in_threadpool(get_retailer_by_email, username)
    if not retailer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    if not verify_password(password, retailer.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    # Create and return JWT token
    access_token = create_access_token(data={"sub": retailer.mail, "role": "retailer"})
    return {"access_token": access_token, "token_type": "bearer"}

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
    username: Annotated[str, Form()], 
    password: Annotated[str, Form()]
):
    
    wholesaler = await run_in_threadpool(get_wholesaler_by_email, username)
    if not wholesaler:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    if not verify_password(password, wholesaler.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    # Create and return JWT token
    access_token = create_access_token(data={"sub": wholesaler.mail, "role": "wholesaler"})
    return {"access_token": access_token, "token_type": "bearer"}


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


# -------------------------------------------------------------------------------------------------------------------------------------------------


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


# -------------------------------------------------------------------------------------------------------------------------------------------------



# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------