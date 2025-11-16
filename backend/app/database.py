# Defining functions to create tables in backend

from sqlmodel import SQLModel,create_engine , Session , select
# SQLModel - for ORM
# Session - for DB Sessions
# select - for queries
from typing import Optional

from db_models import (
    Customer, 
    Retailer,         
    Wholesaler,       
    Product, 
    ShoppingCart, 
    ShoppingCartItem,
    Category,         
    OrderRecords,     
    OrderItem,        
    Feedback,         
    WholesaleOrder,   
    WholesaleOrderItem 
)

# File Path of our Database
file_path = ".sqlite:///..data/livemart.db"

# Creating a DB Engine
engine = create_engine(file_path , echo=True , connect_args={"check_same_thread" : False})  # "echo=True" prints SQL queries to console


# -------------------------------------------------------------------------------------------------------------------------
# Creating Tables
# -------------------------------------------------------------------------------------------------------------------------

def create_db_and_tables():

    # Creating all the tables in the models.py
    SQLModel.metadata.create_all(engine)


#--------------------------------------------------------------------------------------------------------------------------------------------
# Customer Functions


# Function to make a customer table
def add_customer(name: str , mail: str , hashed_password: str , delivery_address: str = None , city:str = None , state:str = None , 
                 pincode:str = None , phone_number:str = None , profile_pic : str = None, 
                 lat: Optional[float] = None, lon: Optional[float] = None):
    

     customer = Customer(
        name = name,                     
        mail = mail,                     
        hashed_password = hashed_password, 
        profile_pic=profile_pic,
        delivery_address = delivery_address, 
        city = city,                       
        state = state,                     
        pincode = pincode,                 
        phone_number = phone_number,      
        no_of_purchases = 0,                 # Initial purchases is zero
        lat = lat,
        lon = lon
     )

     # Creating the table
     with Session(engine) as session: # Opening a session to interact with DB
          session.add(customer)
          session.commit()
          session.refresh(customer)
          return customer
     

# Function to check if a customer already exists with the given mail
def get_customer_by_email(mail: str):

     with Session(engine) as session:
          cust = session.exec(
               select(Customer).where(Customer.mail == mail)
               ).first()
          return cust 
          # Returns the customer if found, else returns None

#--------------------------------------------------------------------------------------------------------------------------------------------
# Retailer Functions

# Function to make retailer table
def add_retailer(name: str, mail: str, hashed_password: str, business_name: str,address: str, city: str, state: str, pincode: str,
                 phone_number: str = None, tax_id: str = None, profile_pic: str = None, business_logo: str = None,
                 lat: Optional[float] = None, lon: Optional[float] = None):
    
    retailer = Retailer(
        name=name,
        mail=mail,
        hashed_password=hashed_password,
        business_name=business_name,
        address=address,
        city=city,
        state=state,
        pincode=pincode,
        phone_number=phone_number,
        tax_id=tax_id,
        profile_pic=profile_pic,
        business_logo=business_logo,
        lat = lat,
        lon = lon
    )

    with Session(engine) as session:
        session.add(retailer)
        session.commit()
        session.refresh(retailer)
        return retailer


# Function to check if retailer already exists
def get_retailer_by_email(mail: str):
    with Session(engine) as session:
        retailer = session.exec(
            select(Retailer).where(Retailer.mail == mail)
        ).first()
        return retailer

#--------------------------------------------------------------------------------------------------------------------------------------------
# Wholesaler Functions


# Adding wholesaler table
def add_wholesaler(name: str, mail: str, hashed_password: str, business_name: str,
                   address: str, city: str, state: str, pincode: str,
                   phone_number: str = None, tax_id: str = None, 
                   profile_pic: str = None, business_logo: str = None,
                   lat: Optional[float] = None, lon: Optional[float] = None):
    
    wholesaler = Wholesaler(
        name=name,
        mail=mail,
        hashed_password=hashed_password,
        business_name=business_name,
        address=address,
        city=city,
        state=state,
        pincode=pincode,
        phone_number=phone_number,
        tax_id=tax_id,
        profile_pic=profile_pic,
        business_logo=business_logo,
        lat = lat,
        lon = lon
    )
    with Session(engine) as session:
        session.add(wholesaler)
        session.commit()
        session.refresh(wholesaler)
        return wholesaler


# Checking if wholesaler already exists
def get_wholesaler_by_email(mail: str):
    with Session(engine) as session:
        wholesaler = session.exec(
            select(Wholesaler).where(Wholesaler.mail == mail)
        ).first()
        return wholesaler

#--------------------------------------------------------------------------------------------------------------------------------------------
# Category Functions

# Function to add a category
def add_category(name: str, description: Optional[str] = None, image_url: Optional[str] = None) -> Category:
    with Session(engine) as session:
        category = Category(name=name, description=description, image_url=image_url)
        session.add(category)
        session.commit()
        session.refresh(category)
        return category

#--------------------------------------------------------------------------------------------------------------------------------------------
# Product Functions

# Function to make a product item
def add_product(name: str, price: float, stock: int, retailer_id: int , description: str = None, category_id: int = None, image_url: Optional[str] = None):
    
    product = Product(
        name=name,
        retailer_id=retailer_id,
        description=description,
        category_id=category_id,
        price=price,
        stock=stock,
        image_url=image_url
    )
    with Session(engine) as session:
        session.add(product)
        session.commit()
        session.refresh(product)
        return product

#--------------------------------------------------------------------------------------------------------------------------------------------
# Shopping Cart Functions


# Function to add a shopping cart

def create_cart_for_customer(customer_id:int):
     
     cart = ShoppingCart(
          customer_id=customer_id,
    )
     
     with Session(engine) as session:
          session.add(cart)
          session.commit()
          session.refresh(cart)
          return cart
     

# Shopping Cart Function (To Access/Retrieve items from the cart)
def get_cart_items(cart_id:int):
     
     with Session(engine) as session:
        items = session.exec(
            select(ShoppingCartItem).where(ShoppingCartItem.cart_id == cart_id)
        ).all()

        return items
     

# To get cart size
def get_cart_size(cart_id:int):
     
    items = get_cart_items(cart_id)      
    size = 0
    for item in items:
         size += item.quantity

    return size


# Adding an item to a cart
def add_item_to_cart(product_id:int ,quantity:int , cart_id:int):


    with Session(engine) as session:
          stmt = select(ShoppingCartItem).where(
               (ShoppingCartItem.cart_id == cart_id) & (ShoppingCartItem.product_id == product_id)
          )
          existing = session.exec(stmt).first()
          if existing:
               existing.quantity += quantity
               session.add(existing)
               session.commit()
               session.refresh(existing)
               return existing
          cart_item = ShoppingCartItem(product_id=product_id, quantity=quantity, cart_id=cart_id)
          session.add(cart_item)
          session.commit()
          session.refresh(cart_item)
          return cart_item