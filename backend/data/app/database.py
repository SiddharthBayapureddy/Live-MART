# Defining functions to create tables in backend

from sqlmodel import SQLModel,create_engine , Session , select
# SQLModel - for ORM
# Session - for DB Sessions
# select - for queries
from typing import Optional, List

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
from schemas import OrderCreate, ProductUpdate, OrderStatusUpdate # Import new schemas

from fastapi import HTTPException, status # For error handling in transactions

# File Path of our Database
file_path = "sqlite:///../data/livemart.db"

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

# Function to get a single product by its ID
def get_product_by_id(product_id: int) -> Optional[Product]:
     with Session(engine) as session:
          return session.get(Product, product_id)

# Function to get all products for a specific retailer
def get_products_by_retailer(retailer_id: int) -> List[Product]:
    with Session(engine) as session:
        statement = select(Product).where(Product.retailer_id == retailer_id)
        return session.exec(statement).all()

# Function to update a product
def update_product_details(product: Product, update_data: ProductUpdate) -> Product:
    with Session(engine) as session:
        # Get the non-None values from the update_data schema
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(product, key, value)
        
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

# Function to get a customer's cart
def get_cart_by_customer_id(customer_id: int) -> Optional[ShoppingCart]:
     with Session(engine) as session:
          statement = select(ShoppingCart).where(ShoppingCart.customer_id == customer_id)
          return session.exec(statement).first()
     

# Shopping Cart Function (To Access/Retrieve items from the cart)
def get_cart_items(cart_id:int):
     
     with Session(engine) as session:
        items = session.exec(
            select(ShoppingCartItem).where(ShoppingCartItem.cart_id == cart_id)
        ).all()

        return items

# Function to get cart items with full product details
def get_detailed_cart_items(cart_id: int) -> List[dict]:
    with Session(engine) as session:
        statement = select(ShoppingCartItem, Product).where(
            ShoppingCartItem.cart_id == cart_id
        ).join(Product, ShoppingCartItem.product_id == Product.id)
        
        results = session.exec(statement).all()
        
        # Format the results into a more useful structure
        detailed_items = []
        for cart_item, product in results:
            detailed_items.append({
                "cart_item_id": cart_item.id,
                "quantity": cart_item.quantity,
                "product": product # This will be a ProductRead schema compatible object
            })
        return detailed_items
     

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
          
          # First, check if product exists and has stock
          product = session.get(Product, product_id)
          if not product:
               raise HTTPException(status_code=404, detail="Product not found")
          
          
          stmt = select(ShoppingCartItem).where(
               (ShoppingCartItem.cart_id == cart_id) & (ShoppingCartItem.product_id == product_id)
          )
          existing = session.exec(stmt).first()

          new_quantity = quantity
          if existing:
               new_quantity += existing.quantity
          
          if product.stock < new_quantity:
               raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}. Available: {product.stock}")

          if existing:
               existing.quantity = new_quantity
               session.add(existing)
               session.commit()
               session.refresh(existing)
               return existing
          
          cart_item = ShoppingCartItem(product_id=product_id, quantity=quantity, cart_id=cart_id)
          session.add(cart_item)
          session.commit()
          session.refresh(cart_item)
          return cart_item

# --------------------------------------------------------------------------------------------------------------------------------------------
# Order and Checkout Functions

def process_checkout(customer: Customer, order_details: OrderCreate) -> OrderRecords:
    
    with Session(engine) as session:
        
        # 1. Get Customer's Cart
        cart = session.exec(select(ShoppingCart).where(ShoppingCart.customer_id == customer.id)).first()
        if not cart:
            raise HTTPException(status_code=404, detail="Customer cart not found")
            
        cart_items = session.exec(select(ShoppingCartItem).where(ShoppingCartItem.cart_id == cart.id)).all()
        if not cart_items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        total_price = 0.0
        products_to_update = []
        order_items_to_create = []

        # 2. Verify stock and calculate total price
        for item in cart_items:
            product = session.get(Product, item.product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product with ID {item.product_id} not found")
            
            if product.stock < item.quantity:
                raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}. Available: {product.stock}")
            
            # Reduce stock
            product.stock -= item.quantity
            products_to_update.append(product)
            
            # Calculate price
            price_at_purchase = product.price
            total_price += price_at_purchase * item.quantity
            
            # Prepare OrderItem
            order_items_to_create.append(
                OrderItem(
                    product_id=product.id,
                    quantity=item.quantity,
                    price_at_purchase=price_at_purchase
                )
            )

        # 3. Create the OrderRecord
        new_order = OrderRecords(
            customer_id=customer.id,
            shipping_address=order_details.shipping_address,
            shipping_city=order_details.shipping_city,
            shipping_pincode=order_details.shipping_pincode,
            total_price=total_price,
            payment_mode=order_details.payment_mode,
            payment_status="Pending" # Or "Completed" if payment is successful
        )
        session.add(new_order)
        session.commit()
        session.refresh(new_order)
        
        # 4. Create OrderItems and link to the new OrderRecord
        for oi in order_items_to_create:
            oi.orderrecords_id = new_order.id
            session.add(oi)
            
        # 5. Update product stock
        for prod in products_to_update:
            session.add(prod)
            
        # 6. Clear the cart
        for item in cart_items:
            session.delete(item)
            
        # 7. Update customer purchase count
        customer.no_of_purchases += 1
        session.add(customer)

        # 8. Commit the entire transaction
        session.commit()
        session.refresh(new_order)
        
        return new_order

# Function to get a single order by ID
def get_order_by_id(order_id: int) -> Optional[OrderRecords]:
    with Session(engine) as session:
        return session.get(OrderRecords, order_id)

# Function to update an order's status
def update_order_status(order: OrderRecords, status_update: OrderStatusUpdate) -> OrderRecords:
    with Session(engine) as session:
        order.status = status_update.status
        if status_update.payment_status:
            order.payment_status = status_update.payment_status
        
        session.add(order)
        session.commit()
        session.refresh(order)
        return order

# Function to get all orders that contain a product from a specific retailer
def get_orders_by_retailer(retailer_id: int) -> List[OrderRecords]:
    with Session(engine) as session:
        # Find all product IDs for this retailer
        product_ids = session.exec(
            select(Product.id).where(Product.retailer_id == retailer_id)
        ).all()
        
        if not product_ids:
            return []
            
        # Find all order IDs that contain at least one of these products
        order_ids = session.exec(
            select(OrderItem.orderrecords_id).where(OrderItem.product_id.in_(product_ids))
        ).distinct().all()
        
        if not order_ids:
            return []
            
        # Get the full OrderRecords for those IDs
        statement = select(OrderRecords).where(OrderRecords.id.in_(order_ids))
        orders = session.exec(statement).all()
        
        return orders