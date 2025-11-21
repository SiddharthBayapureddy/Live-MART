# Defining functions to create tables in backend
import os
from sqlmodel import SQLModel, create_engine, Session, select
from typing import Optional, List, Dict, Any
from datetime import datetime

# Import your models
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
from schemas import OrderCreate, ProductUpdate, OrderStatusUpdate

from fastapi import HTTPException, status

# -----------------------------------------------------------------
# ABSOLUTE PATH SETUP (Guarantees backend/data/)
# -----------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_FILE_PATH = os.path.join(DATA_DIR, "livemart.db")
file_path = f"sqlite:///{DB_FILE_PATH}"

engine = create_engine(file_path, echo=True, connect_args={"check_same_thread": False})


# -----------------------------------------------------------------
# Creating Tables
# -----------------------------------------------------------------

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# -----------------------------------------------------------------
# Customer Functions
# -----------------------------------------------------------------
def add_customer(name: str, mail: str, hashed_password: str, delivery_address: str = None, city: str = None, state: str = None, pincode: str = None, phone_number: str = None, lat: float = None, lon: float = None):
    with Session(engine) as session:
        customer = Customer(
            name=name, 
            mail=mail, 
            hashed_password=hashed_password, 
            delivery_address=delivery_address,
            city=city,
            state=state,
            pincode=pincode,
            phone_number=phone_number,
            lat=lat,
            lon=lon
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)
        return customer

def get_customer_by_email(mail: str):
    with Session(engine) as session:
        statement = select(Customer).where(Customer.mail == mail)
        return session.exec(statement).first()

# -----------------------------------------------------------------
# Retailer Functions
# -----------------------------------------------------------------
def add_retailer(name: str, mail: str, hashed_password: str, business_name: str, address: str, city: str, state: str, pincode: str, lat: float = None, lon: float = None):
    with Session(engine) as session:
        retailer = Retailer(
            name=name,
            mail=mail,
            hashed_password=hashed_password,
            business_name=business_name,
            address=address,
            city=city,
            state=state,
            pincode=pincode,
            lat=lat,
            lon=lon
        )
        session.add(retailer)
        session.commit()
        session.refresh(retailer)
        return retailer

def get_retailer_by_email(mail: str):
    with Session(engine) as session:
        statement = select(Retailer).where(Retailer.mail == mail)
        return session.exec(statement).first()

# -----------------------------------------------------------------
# Wholesaler Functions
# -----------------------------------------------------------------
def add_wholesaler(name: str, mail: str, hashed_password: str, business_name: str, address: str, city: str, state: str, pincode: str, lat: float = None, lon: float = None):
    with Session(engine) as session:
        wholesaler = Wholesaler(
            name=name,
            mail=mail,
            hashed_password=hashed_password,
            business_name=business_name,
            address=address,
            city=city,
            state=state,
            pincode=pincode,
            lat=lat,
            lon=lon
        )
        session.add(wholesaler)
        session.commit()
        session.refresh(wholesaler)
        return wholesaler

def get_wholesaler_by_email(mail: str):
    with Session(engine) as session:
        statement = select(Wholesaler).where(Wholesaler.mail == mail)
        return session.exec(statement).first()

# -----------------------------------------------------------------
# Product & Category Functions
# -----------------------------------------------------------------
def add_category(name: str, description: str, image_url: str):
    with Session(engine) as session:
        category = Category(name=name, description=description, image_url=image_url)
        session.add(category)
        session.commit()
        session.refresh(category)
        return category

def add_product(name: str, price: float, stock: int, retailer_id: int, description: str, category_id: int, image_url: str):
    with Session(engine) as session:
        product = Product(
            name=name,
            price=price,
            stock=stock,
            retailer_id=retailer_id,
            description=description,
            category_id=category_id,
            image_url=image_url
        )
        session.add(product)
        session.commit()
        session.refresh(product)
        return product

def get_all_products(category: str = None) -> List[Product]:
    with Session(engine) as session:
        if category and category.lower() != "all":
            # JOIN Product with Category to filter by the Category Name
            statement = select(Product).join(Category).where(Category.name == category)
        else:
            statement = select(Product)
        return session.exec(statement).all()

def get_product_by_id(product_id: int):
    with Session(engine) as session:
        return session.get(Product, product_id)

def get_products_by_retailer(retailer_id: int) -> List[Product]:
    """Fetches all products belonging to a specific retailer."""
    with Session(engine) as session:
        statement = select(Product).where(Product.retailer_id == retailer_id)
        return session.exec(statement).all()

# [RENAMED from update_product to update_product_details to match main.py]
def update_product_details(product_id: int, product_update: ProductUpdate, retailer_id: int):
    with Session(engine) as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if product.retailer_id != retailer_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this product")
        
        product.price = product_update.price
        product.stock = product_update.stock
        session.add(product)
        session.commit()
        session.refresh(product)
        return product

# -----------------------------------------------------------------
# Cart Functions
# -----------------------------------------------------------------
def create_cart_for_customer(customer_id: int):
    with Session(engine) as session:
        cart = ShoppingCart(customer_id=customer_id)
        session.add(cart)
        session.commit()
        return cart

def get_cart_by_customer_id(customer_id: int):
    with Session(engine) as session:
        statement = select(ShoppingCart).where(ShoppingCart.customer_id == customer_id)
        return session.exec(statement).first()

def get_cart_items(customer_id: int):
    with Session(engine) as session:
        statement = select(ShoppingCart).where(ShoppingCart.customer_id == customer_id)
        cart = session.exec(statement).first()
        if not cart:
            return []
        statement_items = select(ShoppingCartItem).where(ShoppingCartItem.shopping_cart_id == cart.id)
        return session.exec(statement_items).all()

def get_detailed_cart_items(customer_id: int) -> List[Dict[str, Any]]:
    """Returns cart items joined with product details."""
    with Session(engine) as session:
        cart = session.exec(select(ShoppingCart).where(ShoppingCart.customer_id == customer_id)).first()
        if not cart:
            return []
        
        statement = select(ShoppingCartItem, Product).join(Product).where(
            ShoppingCartItem.shopping_cart_id == cart.id
        )
        results = session.exec(statement).all()
        
        detailed_items = []
        for item, product in results:
            detailed_items.append({
                "product_id": product.id,
                "name": product.name,
                "price": product.price,
                "image_url": product.image_url,
                "quantity": item.quantity,
                "total_price": product.price * item.quantity
            })
        return detailed_items

def add_item_to_cart(customer_id: int, product_id: int, quantity: int):
    with Session(engine) as session:
        cart = session.exec(select(ShoppingCart).where(ShoppingCart.customer_id == customer_id)).first()
        if not cart:
            cart = ShoppingCart(customer_id=customer_id)
            session.add(cart)
            session.commit()
            session.refresh(cart)
        
        statement = select(ShoppingCartItem).where(
            (ShoppingCartItem.shopping_cart_id == cart.id) & 
            (ShoppingCartItem.product_id == product_id)
        )
        existing_item = session.exec(statement).first()
        
        if existing_item:
            existing_item.quantity += quantity
            session.add(existing_item)
        else:
            new_item = ShoppingCartItem(shopping_cart_id=cart.id, product_id=product_id, quantity=quantity)
            session.add(new_item)
        session.commit()

def get_cart_size(customer_id: int) -> int:
    with Session(engine) as session:
        cart = session.exec(select(ShoppingCart).where(ShoppingCart.customer_id == customer_id)).first()
        if not cart:
            return 0
        items = session.exec(select(ShoppingCartItem).where(ShoppingCartItem.shopping_cart_id == cart.id)).all()
        return sum(item.quantity for item in items)

def clear_cart(customer_id: int):
    with Session(engine) as session:
        cart = session.exec(select(ShoppingCart).where(ShoppingCart.customer_id == customer_id)).first()
        if cart:
            items = session.exec(select(ShoppingCartItem).where(ShoppingCartItem.shopping_cart_id == cart.id)).all()
            for item in items:
                session.delete(item)
            session.commit()

# -----------------------------------------------------------------
# Order Functions (Including Checkout)
# -----------------------------------------------------------------
def process_checkout(customer_id: int, address: str, city: str, pincode: str, payment_mode: str):
    """
    1. Get Cart Items
    2. Calculate Total
    3. Create Order Record
    4. Create Order Items
    5. Decrease Stock
    6. Clear Cart
    """
    with Session(engine) as session:
        # 1. Get Cart
        cart = session.exec(select(ShoppingCart).where(ShoppingCart.customer_id == customer_id)).first()
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")
            
        # Join items with product to get price and check stock
        statement = select(ShoppingCartItem, Product).join(Product).where(
            ShoppingCartItem.shopping_cart_id == cart.id
        )
        cart_items = session.exec(statement).all()
        
        if not cart_items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        # 2. Calculate Total & Check Stock
        total_price = 0.0
        for item, product in cart_items:
            if product.stock < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")
            total_price += product.price * item.quantity

        # 3. Create Order Record
        order = OrderRecords(
            customer_id=customer_id,
            status="Processing",
            shipping_address=address,
            shipping_city=city,
            shipping_pincode=pincode,
            total_price=total_price,
            payment_mode=payment_mode,
            payment_status="Pending" if payment_mode == "Cash on Delivery" else "Completed",
            order_date=datetime.utcnow()
        )
        session.add(order)
        session.commit()
        session.refresh(order)

        # 4. Create Order Items & 5. Decrease Stock
        for item, product in cart_items:
            order_item = OrderItem(
                orderrecords_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                price_at_purchase=product.price
            )
            session.add(order_item)
            
            # Decrease stock
            product.stock -= item.quantity
            session.add(product)
            
        # 6. Clear Cart Items
        for item, _ in cart_items:
            session.delete(item)
            
        # Update customer purchase count
        customer = session.get(Customer, customer_id)
        if customer:
            customer.no_of_purchases += 1
            session.add(customer)

        session.commit()
        return order

def add_order_record(customer_id: int, address: str, city: str, pincode: str, total_price: float, payment_mode: str):
    with Session(engine) as session:
        order = OrderRecords(
            customer_id=customer_id,
            status="Processing",
            shipping_address=address,
            shipping_city=city,
            shipping_pincode=pincode,
            total_price=total_price,
            payment_mode=payment_mode,
            payment_status="Pending"
        )
        session.add(order)
        session.commit()
        session.refresh(order)
        return order

def get_customer_orders(customer_id: int) -> List[OrderRecords]:
    with Session(engine) as session:
        statement = select(OrderRecords).where(OrderRecords.customer_id == customer_id)
        return session.exec(statement).all()

def get_order_by_id(order_id: int) -> Optional[OrderRecords]:
    with Session(engine) as session:
        return session.get(OrderRecords, order_id)

def update_order_status(order: OrderRecords, status_update: OrderStatusUpdate) -> OrderRecords:
    with Session(engine) as session:
        order.status = status_update.status
        if status_update.payment_status:
            order.payment_status = status_update.payment_status
        session.add(order)
        session.commit()
        session.refresh(order)
        return order

def get_orders_by_retailer(retailer_id: int) -> List[OrderRecords]:
    with Session(engine) as session:
        # Find all product IDs for this retailer
        product_ids = session.exec(select(Product.id).where(Product.retailer_id == retailer_id)).all()
        if not product_ids: return []
            
        # Find all order IDs that contain these products
        order_ids = session.exec(select(OrderItem.orderrecords_id).where(OrderItem.product_id.in_(product_ids))).distinct().all()
        if not order_ids: return []
            
        # Get the full OrderRecords
        statement = select(OrderRecords).where(OrderRecords.id.in_(order_ids))
        return session.exec(statement).all()

# -----------------------------------------------------------------
# Feedback & Wholesale Functions
# -----------------------------------------------------------------
def add_feedback(product_id: int, customer_id: int, rating: int, comment: str):
    with Session(engine) as session:
        fb = Feedback(product_id=product_id, customer_id=customer_id, rating=rating, comment=comment)
        session.add(fb)
        session.commit()
        return fb

def add_wholesale_order(retailer_id: int, wholesaler_id: int, address: str, items: list):
    with Session(engine) as session:
        total_price = sum(item['product'].price * item['quantity'] for item in items) * 0.7 
        
        w_order = WholesaleOrder(
            retailer_id=retailer_id,
            wholesaler_id=wholesaler_id,
            status="Processing",
            total_price=total_price,
            shipping_address=address
        )
        session.add(w_order)
        session.commit()
        session.refresh(w_order)
        
        for item in items:
            wo_item = WholesaleOrderItem(
                wholesale_order_id=w_order.id,
                product_id=item['product'].id,
                quantity=item['quantity'],
                price_at_purchase=item['product'].price * 0.7
            )
            session.add(wo_item)
        session.commit()
        return w_order