# App

# Importing FastAPI
from fastapi import FastAPI , HTTPException , status # HTTPException for exception handling

# For file management
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session, select
from contextlib import asynccontextmanager

from fastapi.concurrency import run_in_threadpool

from auth import hash_password, verify_password

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


# Initializing an FastAPI app instance
app = FastAPI(title="Live MART" , lifespan=lifespan)


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

# Login Endpoint - POST ---> Accepts JSON Body
@app.post("/login/customer", tags=["Customer Auth"])
async def login_customer(req : LoginRequest):

    # Checking if customer exists
    customer = await run_in_threadpool(get_customer_by_email , req.mail)

    if not customer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail="Invalid Credentials: Mail not found")
    

    # Checking password
    # Password incorrect
    if not verify_password(req.password, customer.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED , detail="Invalid Credentials: Password not found")
    
    # NOTE: In a real app, you would return a JWT token here
    return {"message": "Login successful", "customer_id": customer.id, "name": customer.name}


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

@app.post("/login/retailer", tags=["Retailer Auth"])
async def login_retailer(req: LoginRequest):
    
    retailer = await run_in_threadpool(get_retailer_by_email, req.mail)
    if not retailer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    if not verify_password(req.password, retailer.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    return {"message": "Login successful", "retailer_id": retailer.id, "business_name": retailer.business_name}

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

@app.post("/login/wholesaler", tags=["Wholesaler Auth"])
async def login_wholesaler(req: LoginRequest):
    
    wholesaler = await run_in_threadpool(get_wholesaler_by_email, req.mail)
    if not wholesaler:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    if not verify_password(req.password, wholesaler.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials")

    return {"message": "Login successful", "wholesaler_id": wholesaler.id, "business_name": wholesaler.business_name}


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
async def create_product_endpoint(product : ProductCreate):
    
    # Correctly passing all arguments from the schema
    new_product = await run_in_threadpool(
        add_product,
        product.name,
        product.price,
        product.stock,
        product.retailer_id,
        product.description,
        product.category_id,
        product.image_url
    )

    if not new_product:
        raise HTTPException(status_code=500 , detail="Failed to create product. Try again! Oops lol")
    
    return new_product


# -------------------------------------------------------------------------------------------------------------------------------------------------


# -------------------------------------------------------------------------------------------------------------------------------------------------


# -------------------------------------------------------------------------------------------------------------------------------------------------



# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------------------------------------