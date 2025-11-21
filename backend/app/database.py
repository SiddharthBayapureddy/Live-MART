# Defining functions to create tables in backend

from sqlmodel import SQLModel, create_engine, Session, select
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

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
# ABSOLUTE PATH SETUP (Guarantees backend/data/livemart.db)
# -----------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_FILE_PATH = os.path.join(DATA_DIR, "livemart.db")
# Use 3 slashes for relative path, 4 for absolute (sqlite:////...) on *nix, 
# but usually 3 works fine if we pass the full path string.
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
def add_customer(name: str, mail: str, hashed_password: str, delivery_address: str = None, city: str = None, state: str = None, pincode: str = None, phone_number: str = None, profile_pic: str = None, lat: float = None, lon: float = None):
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
            profile_pic=profile_pic,
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
def add_retailer(name: str, mail: str, hashed_password: str, business_name: str, address: str, city: str, state: str, pincode: str, phone_number: str = None, tax_id: str = None, profile_pic: str = None, business_logo: str = None, lat: float = None, lon: float = None):
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
            phone_number=phone_number,
            tax_id=tax_id,
            profile_pic=profile_pic,
            business_logo=business_logo,
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
def add_wholesaler(name: str, mail: str, hashed_password: str, business_name: str, address: str, city: str, state: str, pincode: str, phone_number: str = None, tax_id: str = None, profile_pic: str = None, business_logo: str = None, lat: float = None, lon: float = None):
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
            phone_number=phone_number,
            tax_id=tax_id,
            profile_pic=profile_pic,
            business_logo=business_logo,
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
            statement = select(Product).join(Category).where(Category.name == category)
        else:
            statement = select(Product)
        return session.exec(statement).all()

def get_product_by_id(product_id: int):
    with Session(engine) as session:
        return session.get(Product, product_id)

def get_products_by_retailer(retailer_id: int) -> List[Product]:
    with Session(engine) as session:
        statement = select(Product).where(Product.retailer_id == retailer_id)
        return session.exec(statement).all()

def update_product_details(product: Product, update_data: ProductUpdate) -> Product:
    with Session(engine) as session:
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(product, key, value)
        
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
        session.refresh(cart) 
        return cart

def get_cart_by_customer_id(customer_id: int):
    with Session(engine) as session:
        statement = select(ShoppingCart).where(ShoppingCart.customer_id == customer_id)
        return session.exec(statement).first()

def get_cart_items(cart_id: int):
    with Session(engine) as session:
        items = session.exec(
            select(ShoppingCartItem).where(ShoppingCartItem.cart_id == cart_id)
        ).all()
        return items

# FIX: Explicitly accept 'cart_id' to match keyword argument call from main.py
def get_detailed_cart_items(cart_id: int) -> List[dict]:
    with Session(engine) as session:
        statement = select(ShoppingCartItem, Product).where(
            ShoppingCartItem.cart_id == cart_id
        ).join(Product, ShoppingCartItem.product_id == Product.id)
        
        results = session.exec(statement).all()
        
        detailed_items = []
        for cart_item, product in results:
            detailed_items.append({
                "cart_item_id": cart_item.id,
                "quantity": cart_item.quantity,
                "product": product
            })
        return detailed_items

# FIX: Updated signature to accept 'cart_id' and optional 'customer_id'
def add_item_to_cart(product_id: int, quantity: int, cart_id: int, customer_id: int = None):
    with Session(engine) as session:
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
        
        # If quantity becomes <= 0, remove item
        if existing and new_quantity <= 0:
            session.delete(existing)
            session.commit()
            return None

        if product.stock < new_quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}. Available: {product.stock}")

        if existing:
            existing.quantity = new_quantity
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing
        
        if quantity > 0:
            cart_item = ShoppingCartItem(product_id=product_id, quantity=quantity, cart_id=cart_id)
            session.add(cart_item)
            session.commit()
            session.refresh(cart_item)
            return cart_item
        
        return None

def get_cart_size(cart_id: int):
    items = get_cart_items(cart_id)      
    size = 0
    for item in items:
         size += item.quantity
    return size

# -----------------------------------------------------------------
# Order Functions
# -----------------------------------------------------------------
def process_checkout(customer: Customer, order_details: OrderCreate) -> OrderRecords:
    with Session(engine) as session:
        # 1. Get Cart
        cart = session.exec(select(ShoppingCart).where(ShoppingCart.customer_id == customer.id)).first()
        if not cart:
            raise HTTPException(status_code=404, detail="Customer cart not found")
            
        cart_items = session.exec(select(ShoppingCartItem).where(ShoppingCartItem.cart_id == cart.id)).all()
        if not cart_items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        total_price = 0.0
        products_to_update = []
        order_items_to_create = []

        # 2. Calc Total & Check Stock
        for item in cart_items:
            product = session.get(Product, item.product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product with ID {item.product_id} no longer exists")
            
            if product.stock < item.quantity:
                raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}. Available: {product.stock}")
            
            product.stock -= item.quantity
            products_to_update.append(product)
            
            price_at_purchase = product.price
            total_price += price_at_purchase * item.quantity
            
            order_items_to_create.append(
                OrderItem(
                    product_id=product.id,
                    quantity=item.quantity,
                    price_at_purchase=price_at_purchase
                )
            )

        # 3. Create Order
        new_order = OrderRecords(
            customer_id=customer.id,
            shipping_address=order_details.shipping_address,
            shipping_city=order_details.shipping_city,
            shipping_pincode=order_details.shipping_pincode,
            total_price=total_price,
            payment_mode=order_details.payment_mode,
            payment_status="Pending"
        )
        session.add(new_order)
        session.commit()
        session.refresh(new_order)
        
        # 4. Link Order Items
        for oi in order_items_to_create:
            oi.orderrecords_id = new_order.id
            session.add(oi)
            
        # 5. Update Stock
        for prod in products_to_update:
            session.add(prod)
            
        # 6. Clear Cart
        for item in cart_items:
            session.delete(item)
            
        # 7. Update Customer Stats
        customer.no_of_purchases += 1
        session.add(customer)

        session.commit()
        session.refresh(new_order)
        
        return new_order

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
        product_ids = session.exec(select(Product.id).where(Product.retailer_id == retailer_id)).all()
        if not product_ids: return []
            
        order_ids = session.exec(
            select(OrderItem.orderrecords_id).where(OrderItem.product_id.in_(product_ids))
        ).distinct().all()
        if not order_ids: return []
            
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
            delivery_address=address
        )
        session.add(w_order)
        session.commit()
        session.refresh(w_order)
        
        for item in items:
            wo_item = WholesaleOrderItem(
                wholesale_order_id=w_order.id,
                product_id=item['product'].id,
                quantity=item['quantity'],
                price_per_unit=item['product'].price * 0.7
            )
            session.add(wo_item)
        session.commit()
        return w_order