# Database Models

# Here, we define all the database tables, attributes to each

from sqlmodel import SQLModel , Field, Relationship
from typing import Optional ,List  # To allow fields to be NULL
from datetime import datetime # Default timestamps
from pathlib import Path


# File paths for Default Stock images for Profile Picture
STATIC_BASE = Path(".") # Represents the root of the static directory

# Profile Pictures
PFP_DIR = STATIC_BASE / "profile_pictures"
default_pfp_path = str(PFP_DIR / "default.png")

RETAILER_PFP_DIR = PFP_DIR / "retailer_pfps"
default_relailer_shop = str(RETAILER_PFP_DIR / "default_shop.png")

WHOLESALER_PFP_DIR = PFP_DIR / "wholesaler_pfps"
default_wholesaler_shop = str(WHOLESALER_PFP_DIR / "default_shop.png")

# Product/Category Images
PRODUCT_IMG_DIR = STATIC_BASE / "product_images"
default_product_image = str(PRODUCT_IMG_DIR / "default.png")

CATEGORY_IMG_DIR = STATIC_BASE / "category_images"
default_category_image = str(CATEGORY_IMG_DIR / "default.png")


# --------------------------------------------------------------------------------------------------------------------
# Customer Table Definition
# --------------------------------------------------------------------------------------------------------------------

class Customer(SQLModel , table=True):

    # Customer ID -- Primary key as a unique identifier (Auto-generated)
    id: Optional[int] = Field(default=None , primary_key=True)    # Keeping it optional, so it'll autogenerate


    # Personal Details
    name: str
    mail: str
    hashed_password: str  # Hashed password for secure authenticaion
    profile_pic : Optional[str] = Field(default=default_pfp_path)

    date_joined: datetime = Field(default_factory=datetime.utcnow , nullable=False)

    # Address Details
    delivery_address: Optional[str] = None
    city : Optional[str] = None
    state : Optional[str] = None
    pincode: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

    # Contact Details
    phone_number: Optional[str] = None

    # Additional Details
    no_of_purchases : int = 0
    preferences: Optional[str] = None

    is_verified: bool = Field(default=False)


# --------------------------------------------------------------------------------------------------------------------
# Retailer Table Definition
# --------------------------------------------------------------------------------------------------------------------

class Retailer(SQLModel , table=True):

    # Retailer ID - Primary key
    id: Optional[int] = Field(default=None , primary_key=True)

    name: str
    mail : str
    hashed_password : str
    profile_pic : Optional[str] = Field(default=default_pfp_path)

    date_joined: datetime = Field(default_factory=datetime.utcnow , nullable=False)


    # Contact
    business_name : str
    business_logo : Optional[str] = Field(default=default_relailer_shop)
    business_description : Optional[str] = None
    phone_number: Optional[str] = None
    tax_id : Optional[str] = None

    # Address details
    address: str 
    city: str
    state: str
    pincode: str
    lat: Optional[float] = None
    lon: Optional[float] = None

    is_active : bool = True

    is_verified: bool = Field(default=False)



# --------------------------------------------------------------------------------------------------------------------
# Wholesaler Table Definition 
# --------------------------------------------------------------------------------------------------------------------

class Wholesaler(SQLModel, table=True):

    # Wholesaler ID - Primary key
    id: Optional[int] = Field(default=None, primary_key=True)

    name: str
    mail: str
    hashed_password: str
    profile_pic : Optional[str] = Field(default=default_pfp_path)

    date_joined: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Contact
    business_name: str
    business_logo: Optional[str] = Field(default=default_wholesaler_shop)
    business_description: Optional[str] = None

    tax_id: Optional[str] = None # For business verification


    phone_number: Optional[str] = None
    # Address details
    address: str
    city: str
    state: str
    pincode: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    
    is_active: bool = True

    is_verified: bool = Field(default=False)



# --------------------------------------------------------------------------------------------------------------------
# Wholesale Order Table Definition 
# --------------------------------------------------------------------------------------------------------------------
class WholesaleOrder(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Retailer --> Customer
    retailer_id: int = Field(foreign_key="retailer.id")
    
    # Wholesaler --> Seller
    wholesaler_id: int = Field(foreign_key="wholesaler.id")
    
    order_date: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    status: str = Field(default="Pending") # "Pending", "Approved", "Shipped"
    total_price: float
    
    # Address for the wholesaler to ship to
    delivery_address: Optional[str] = Field(default=None)


# --- Wholesaler Specific Inventory ---
class WholesalerProduct(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    wholesaler_id: int = Field(foreign_key="wholesaler.id")
    name: str
    price: float  # Bulk price per unit
    stock: int    # Total units available
    min_qty: int = Field(default=10) # Minimum order quantity
    image_url: Optional[str] = Field(default="product_images/default.png")




# --------------------------------------------------------------------------------------------------------------------
# Wholesale Order Item Table Definition (NEW)
# --------------------------------------------------------------------------------------------------------------------
class WholesaleOrderItem(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    wholesale_order_id: int = Field(foreign_key="wholesaleorder.id")
    
    # This could link to the main Product table OR a separate WholesalerProduct table
    # For simplicity in your project, let's link to a main product.
    # This implies wholesalers and retailers sell from the same product catalog,
    # which might be an assumption you make.
    #
    # A better model for proxy stock (source 44) would be a separate
    # 'WholesalerProduct' table, but let's keep it simpler for now.
    
    product_id: int = Field(foreign_key="product.id")
    quantity: int
    price_per_unit: float
    

# --------------------------------------------------------------------------------------------------------------------
# Product Table Definition
# --------------------------------------------------------------------------------------------------------------------

class Product(SQLModel , table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    
    name: str
    description: Optional[str] = None

    category_id: Optional[int] = Field(default=None, foreign_key="category.id")

    price: float
    stock: int
    
    image_url: Optional[str] = Field(default=default_product_image)
    cart_items: List["ShoppingCartItem"] = Relationship(back_populates="product")
    # Linking product to retailer who sells it
    retailer_id : int = Field(foreign_key="retailer.id")



# Category Model
class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: Optional[str] = None
    image_url: Optional[str] = Field(default=default_category_image)


# --------------------------------------------------------------------------------------------------------------------
# Shopping Cart Table Definition
# --------------------------------------------------------------------------------------------------------------------

class ShoppingCart(SQLModel , table=True):

    id: Optional[int] = Field(default=None , primary_key=True)
    items: List["ShoppingCartItem"] = Relationship(back_populates="shopping_cart")
    # Refers to the Customer using this cart
    customer_id: int = Field(foreign_key="customer.id")



# --------------------------------------------------------------------------------------------------------------------
# Shopping Cart Item Table Definition
# --------------------------------------------------------------------------------------------------------------------

class ShoppingCartItem(SQLModel , table = True):

    id: Optional[int] = Field(default=None , primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    quantity: int

    # Refers to the shopping cart the item belongs to
    cart_id: int = Field(foreign_key="shoppingcart.id")
    # Relationships:
    # 1. Relation to Product (Required for the ShoppingCartItemRead schema)
    product: "Product" = Relationship(back_populates="cart_items")
    # 2. Relation to ShoppingCart
    shopping_cart: "ShoppingCart" = Relationship(back_populates="items")



# --------------------------------------------------------------------------------------------------------------------
# Order Records Table Definition
# --------------------------------------------------------------------------------------------------------------------

# Keeps a record of all orders that went through
class OrderRecords(SQLModel , table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")

    order_date : datetime = Field (default_factory=datetime.utcnow , nullable=False)
    status: str = Field(default="Pending")

    shipping_address: str 
    shipping_city: str
    shipping_pincode: str

    total_price : float

    payment_mode: str
    payment_status: str = Field(default="Pending")


# --------------------------------------------------------------------------------------------------------------------
# Order Item Table Definition 
# --------------------------------------------------------------------------------------------------------------------
class OrderItem(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    orderrecords_id: int = Field(foreign_key="orderrecords.id")
    product_id: int = Field(foreign_key="product.id")
    quantity: int
    
    # Store the price at the time of purchase, in case the Product.price changes later
    price_at_purchase: float




# --------------------------------------------------------------------------------------------------------------------
# Feedback/Review Table Definition 
# --------------------------------------------------------------------------------------------------------------------
class Feedback(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    customer_id: int = Field(foreign_key="customer.id")
    
    rating: int # A rating, e.g., 1-5 stars
    comment: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)



# --------------------------------------------------------------------------------------------------------------------
# OTP Model
# --------------------------------------------------------------------------------------------------------------------

class PasswordReset(SQLModel , table=True):
    id : Optional[int] = Field(default=None , primary_key=True)
    email: str = Field(index=True)
    otp:str
    expires_at : datetime
    
class VerificationOTP(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    otp: str
    expires_at: datetime