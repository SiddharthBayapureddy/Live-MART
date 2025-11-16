# Used for validating and structuring the data my API recieves and returns


    # BaseModel for defining request/response schemas
from pydantic import BaseModel , EmailStr   # EmailStr helps validate proper email structure
from typing import Optional , List
from datetime import datetime

# --------------------------------------------------------------------------------------------------------------------------------------------

# -----------------------------
# Customer Schemas
# -----------------------------

# Scheme for new SignUp Customers
class CustomerCreate(BaseModel):

    name : str
    mail : EmailStr
    password : str
    delivery_address: Optional[str] = None  
    city: Optional[str] = None            
    state: Optional[str] = None           
    pincode: Optional[str] = None         
    phone_number: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

# --------------------------------------------------------------------------------------------------------------------------------------------

# Scheme for returning Customer Info
class CustomerRead(BaseModel):

    id : int 
    name : str
    mail : EmailStr
    delivery_address: Optional[str] = None  
    city: Optional[str] = None            
    state: Optional[str] = None           
    pincode: Optional[str] = None         
    phone_number: Optional[str] = None
    no_of_purchases : int 
    preferences: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

    profile_pic : Optional[str]
    date_joined : datetime

    class Config:
        orm_mode = True    # Allows returning SQLModel objects directlty

# --------------------------------------------------------------------------------------------------------------------------------------------
# Retailer Schemas

class RetailerCreate(BaseModel):
    name: str
    mail: EmailStr
    password: str
    business_name: str
    address: str 
    city: str
    state: str
    pincode: str
    phone_number: Optional[str] = None
    tax_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

class RetailerRead(BaseModel):
    id: int
    name: str
    mail: EmailStr
    profile_pic: Optional[str] = None
    date_joined: datetime
    business_name: str
    business_logo: Optional[str] = None
    business_description: Optional[str] = None
    phone_number: Optional[str] = None
    tax_id: Optional[str] = None
    address: str 
    city: str
    state: str
    pincode: str
    is_active: bool
    lat: Optional[float] = None
    lon: Optional[float] = None

    class Config:
        orm_mode = True

# --------------------------------------------------------------------------------------------------------------------------------------------

# Wholesaler Scheme

class WholesalerCreate(BaseModel):
    name: str
    mail: EmailStr
    password: str
    business_name: str
    address: str 
    city: str
    state: str
    pincode: str
    phone_number: Optional[str] = None
    tax_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

class WholesalerRead(BaseModel):
    id: int
    name: str
    mail: EmailStr
    profile_pic: Optional[str] = None
    date_joined: datetime
    business_name: str
    business_logo: Optional[str] = None
    business_description: Optional[str] = None
    phone_number: Optional[str] = None
    tax_id: Optional[str] = None
    address: str 
    city: str
    state: str
    pincode: str
    is_active: bool
    lat: Optional[float] = None
    lon: Optional[float] = None

    class Config:
        orm_mode = True


# --------------------------------------------------------------------------------------------------------------------------------------------

class LoginRequest(BaseModel):
    mail: EmailStr
    password: str

# --------------------------------------------------------------------------------------------------------------------------------------------

class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int
    retailer_id: int 
    description: Optional[str] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = None

# --------------------------------------------------------------------------------------------------------------------------------------------

class ProductRead(BaseModel):
    id: int
    name: str
    price: float
    stock: int
    description: Optional[str] = None
    category_id: Optional[int] = None
    retailer_id: int
    image_url: Optional[str]

    class Config:
        orm_mode = True

# --------------------------------------------------------------------------------------------------------------------------------------------

# Category Schemas

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None

class CategoryRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    image_url: Optional[str]

    class Config:
        orm_mode = True

# --------------------------------------------------------------------------------------------------------------------------------------------




# --------------------------------------------------------------------------------------------------------------------------------------------



# --------------------------------------------------------------------------------------------------------------------------------------------

# Schema for creating a ShoppingCartItem
class ShoppingCartItemCreate(BaseModel):

    product_id : int
    quantity: int

# --------------------------------------------------------------------------------------------------------------------------------------------

# Schema for reading a ShoppingCartItem
class ShoppingCartItemRead(BaseModel):

    id: int                     
    product_id: int             
    quantity: int
    cart_id: int

    class Config:
        orm_mode = True          

# --------------------------------------------------------------------------------------------------------------------------------------------

# Order and OrderRecords Schemas

# Schema for reading a single order item
class OrderItemRead(BaseModel):
    id: int
    product_id: int
    quantity: int
    price_at_purchase: float

    class Config:
        orm_mode = True

# Schema for creating a new order (checkout)
class OrderCreate(BaseModel):
    # Customer ID will come from logged-in user
    # We'll get the address details from their user profile or this request
    shipping_address: str 
    shipping_city: str
    shipping_pincode: str
    payment_mode: str # e.g., "Online" or "Offline" (source 51)

# Schema for reading a complete order record
class OrderRecordsRead(BaseModel):
    id: int
    customer_id: int
    order_date: datetime
    status: str
    shipping_address: str 
    shipping_city: str
    shipping_pincode: str
    total_price: float
    payment_mode: str
    payment_status: str
    
    # We can also return the list of items in this order
    # To do this, we need to define OrderItemRead *before* this schema
    items: List[OrderItemRead] = [] # This field is not in the DB model,
                                # but we will populate it in our API endpoint

    class Config:
        orm_mode = True

# --------------------------------------------------------------------------------------------------------------------------------------------
# Feedback Schemas 

class FeedbackCreate(BaseModel):
    rating: int
    comment: Optional[str] = None
    # product_id and customer_id will come from the URL and logged-in user

class FeedbackRead(BaseModel):
    id: int
    product_id: int
    customer_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    
    customer_name: str 

    class Config:
        orm_mode = True






# --------------------------------------------------------------------------------------------------------------------------------------------