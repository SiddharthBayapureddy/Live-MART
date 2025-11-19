# advanced_populate.py
# A comprehensive seeder for the Live MART database.
# This script creates a large, interconnected set of sample data
# without using any external libraries (like 'faker').

import os
import random
from datetime import datetime, timedelta
from typing import Optional

# SQLModel imports
from sqlmodel import Session, SQLModel, create_engine, select

# Import all database models
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

# Import all database "add" functions and the engine
from database import (
    engine, # Use the same engine as the main app
    create_db_and_tables,
    add_customer,
    add_retailer,
    add_wholesaler,
    add_product,
    add_category,
    create_cart_for_customer
)

# Import the password hashing function
from auth import hash_password

# --- Sample Data Lists (No Faker) ---

SAMPLE_FIRST_NAMES = ["John", "Jane", "Alex", "Emily", "Chris", "Katie", "Michael", "Sarah", "David", "Laura", "Robert", "Jennifer"]
SAMPLE_LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
SAMPLE_CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"]
SAMPLE_STATES = ["NY", "CA", "IL", "TX", "AZ", "PA", "TX", "CA", "TX", "CA"]
SAMPLE_STREET_NAMES = ["Main St", "Oak Ave", "Pine St", "Maple Dr", "Cedar Ln", "Elm St", "Washington Blvd", "Lakeview Ter"]

# Lat/Lon pairs roughly corresponding to the sample cities
SAMPLE_LAT_LON = [
    (40.7128, -74.0060), (34.0522, -118.2437), (41.8781, -87.6298), (29.7604, -95.3698), (33.4484, -112.0740),
    (39.9526, -75.1652), (29.4241, -98.4936), (32.7157, -117.1611), (32.7767, -96.7970), (37.3382, -121.8863)
]

SAMPLE_CATEGORIES = [
    ("Electronics", "Gadgets, computers, and more", "category_images/electronics.jpg"),
    ("Groceries", "Fresh produce, dairy, and pantry items", "category_images/groceries.jpg"),
    ("Fashion", "Apparel, shoes, and accessories", "category_images/fashion.jpg"),
    ("Home & Kitchen", "Furniture, decor, and appliances", "category_images/home.jpg"),
    ("Books", "Fiction, non-fiction, and textbooks", "category_images/books.jpg"),
    ("Sports & Outdoors", "Equipment, activewear, and gear", "category_images/sports.jpg")
]
SAMPLE_PRODUCT_ADJECTIVES = ["Wireless", "Smart", "Ergonomic", "Organic", "Handcrafted", "Heavy Duty", "Premium", "Bluetooth", "LED", "Eco-Friendly"]
SAMPLE_PRODUCT_NOUNS = ["Mouse", "Keyboard", "Headphones", "T-Shirt", "Coffee Beans", "Running Shoes", "Backpack", "Water Bottle", "Desk Lamp", "Yoga Mat"]

# Sample product images
SAMPLE_PRODUCT_IMAGES = [
    "product_images/mouse.jpg",
    "product_images/keyboard.jpg",
    "product_images/headphones.jpg",
    "product_images/tshirt.jpg",
    "product_images/coffee.jpg",
    "product_images/shoes.jpg",
    "product_images/backpack.jpg",
    "product_images/bottle.jpg",
    "product_images/lamp.jpg",
    "product_images/yogamat.jpg"
]

SAMPLE_BIZ_ADJECTIVES = ["Global", "National", "Apex", "Summit", "Dynamic", "Pinnacle", "United", "Premier", "Elite"]
SAMPLE_BIZ_NOUNS = ["Supplies", "Solutions", "Logistics", "Ventures", "Trading", "Imports", "Wholesale", "Enterprises"]
SAMPLE_COMMENTS = [
    "Great product! Highly recommend.",
    "It's okay, not what I expected.",
    "Five stars! Would buy again.",
    "Arrived late and the box was damaged.",
    "Good value for the price.",
    "Changed my life! Amazing!",
    "Smaller than it looks in the picture."
]

# --- Helper functions (for models missing 'add' functions in database.py) ---

def add_order(customer_id: int, address_info: dict, total_price: float, payment_mode: str, items: list) -> OrderRecords:
    with Session(engine) as session:
        # 1. Create the OrderRecord
        order = OrderRecords(
            customer_id=customer_id,
            status=random.choice(["Delivered", "Shipped", "Processing"]),
            shipping_address=address_info["address"],
            shipping_city=address_info["city"],
            shipping_pincode=address_info["pincode"],
            total_price=total_price,
            payment_mode=payment_mode,
            payment_status="Completed",
            order_date=datetime.utcnow() - timedelta(days=random.randint(1, 90)) # Past order
        )
        session.add(order)
        session.commit()
        session.refresh(order)

        # 2. Add OrderItems
        for item in items:
            order_item = OrderItem(
                orderrecords_id=order.id,
                product_id=item["product"].id,
                quantity=item["quantity"],
                price_at_purchase=item["product"].price
            )
            session.add(order_item)
        
        session.commit()
        return order

def add_feedback(product_id: int, customer_id: int, rating: int, comment: str) -> Feedback:
    with Session(engine) as session:
        feedback = Feedback(
            product_id=product_id,
            customer_id=customer_id,
            rating=rating,
            comment=comment
        )
        session.add(feedback)
        session.commit()
        session.refresh(feedback)
        return feedback

def add_wholesale_order(retailer_id: int, wholesaler_id: int, address: str, items: list) -> WholesaleOrder:
    with Session(engine) as session:
        total_price = sum(item["product"].price * 0.7 * item["quantity"] for item in items) # 70% of retail price
        
        order = WholesaleOrder(
            retailer_id=retailer_id,
            wholesaler_id=wholesaler_id,
            status=random.choice(["Delivered", "Approved", "Shipped"]),
            total_price=total_price,
            delivery_address=address,
            order_date=datetime.utcnow() - timedelta(days=random.randint(5, 60))
        )
        session.add(order)
        session.commit()
        session.refresh(order)
        
        for item in items:
            order_item = WholesaleOrderItem(
                wholesale_order_id=order.id,
                product_id=item["product"].id,
                quantity=item["quantity"],
                price_per_unit=item["product"].price * 0.7
            )
            session.add(order_item)
        
        session.commit()
        return order

def get_random_address() -> dict:
    idx = random.randint(0, len(SAMPLE_CITIES) - 1)
    city = SAMPLE_CITIES[idx]
    state = SAMPLE_STATES[idx]
    lat, lon = SAMPLE_LAT_LON[idx]
    
    return {
        "address": f"{random.randint(100, 9999)} {random.choice(SAMPLE_STREET_NAMES)}",
        "city": city,
        "state": state,
        "pincode": str(random.randint(10000, 99999)),
        "lat": lat + random.uniform(-0.05, 0.05), # Add jitter
        "lon": lon + random.uniform(-0.05, 0.05)  # Add jitter
    }

# --- Main Seeder Function ---

def seed():
    DB_FILE = "../data/livemart.db" # Adjusted path to match your project
    DB_DIR = os.path.dirname(DB_FILE)
    
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    print("Removed old database.")

    # Re-create tables
    create_db_and_tables()
    print("Created new tables.")

    # Lists to store created objects
    categories = []
    wholesalers = []
    retailers = []
    products = []
    customers = []

    print("--- 1. Creating Categories ---")
    for name, desc, img in SAMPLE_CATEGORIES:
        cat = add_category(name, desc, img)
        categories.append(cat)
    print(f"Created {len(categories)} categories.")

    print("--- 2. Creating Wholesalers ---")
    for i in range(5):
        addr = get_random_address()
        w = add_wholesaler(
            name=f"{random.choice(SAMPLE_FIRST_NAMES)} {random.choice(SAMPLE_LAST_NAMES)}",
            mail=f"wholesaler{i+1}@supply.com",
            hashed_password=hash_password("whole123"),
            business_name=f"{random.choice(SAMPLE_BIZ_ADJECTIVES)} {random.choice(SAMPLE_BIZ_NOUNS)}",
            address=addr["address"],
            city=addr["city"],
            state=addr["state"],
            pincode=addr["pincode"],
            lat=addr["lat"],
            lon=addr["lon"]
        )
        wholesalers.append(w)
    print(f"Created {len(wholesalers)} wholesalers.")

    print("--- 3. Creating Retailers ---")
    for i in range(15):
        addr = get_random_address()
        r = add_retailer(
            name=f"{random.choice(SAMPLE_FIRST_NAMES)} {random.choice(SAMPLE_LAST_NAMES)}",
            mail=f"retailer{i+1}@shop.com",
            hashed_password=hash_password("retail123"),
            business_name=f"{random.choice(SAMPLE_PRODUCT_NOUNS)} Mart",
            address=addr["address"],
            city=addr["city"],
            state=addr["state"],
            pincode=addr["pincode"],
            lat=addr["lat"],
            lon=addr["lon"]
        )
        retailers.append(r)
    print(f"Created {len(retailers)} retailers.")

    print("--- 4. Creating Products ---")
    for i in range(100):
        prod = add_product(
            name=f"{random.choice(SAMPLE_PRODUCT_ADJECTIVES)} {random.choice(SAMPLE_PRODUCT_NOUNS)}",
            price=round(random.uniform(5.99, 499.99), 2),
            stock=random.randint(10, 200),
            retailer_id=random.choice(retailers).id,
            description="A high-quality product.",
            category_id=random.choice(categories).id,
            image_url=random.choice(SAMPLE_PRODUCT_IMAGES)
        )
        products.append(prod)
    print(f"Created {len(products)} products.")

    print("--- 5. Creating Customers ---")
    for i in range(50):
        addr = get_random_address()
        c = add_customer(
            name=f"{random.choice(SAMPLE_FIRST_NAMES)} {random.choice(SAMPLE_LAST_NAMES)}",
            mail=f"customer{i+1}@gmail.com",
            hashed_password=hash_password("cust123"),
            delivery_address=addr["address"],
            city=addr["city"],
            state=addr["state"],
            pincode=addr["pincode"],
            phone_number=f"555-{random.randint(100,999)}-{random.randint(1000,9999)}",
            lat=addr["lat"],
            lon=addr["lon"]
        )
        # Create an empty cart for them
        create_cart_for_customer(c.id)
        customers.append(c)
    print(f"Created {len(customers)} customers (and their carts).")

    print("--- 6. Creating Past Orders (for history) ---")
    order_count = 0
    with Session(engine) as session: # Use one session for efficiency
        for cust in customers:
            # Each customer has 0 to 5 past orders
            for _ in range(random.randint(0, 5)):
                items_in_order = []
                total_price = 0
                for _ in range(random.randint(1, 4)): # 1-4 items per order
                    prod = random.choice(products)
                    qty = random.randint(1, 3)
                    items_in_order.append({"product": prod, "quantity": qty})
                    total_price += prod.price * qty
                
                addr = {
                    "address": cust.delivery_address, 
                    "city": cust.city, 
                    "pincode": cust.pincode
                }
                
                # We can't use the add_order helper if we want to update the customer
                # in the same session, so we do the logic here.
                order = OrderRecords(
                    customer_id=cust.id,
                    status=random.choice(["Delivered", "Shipped"]),
                    shipping_address=addr["address"],
                    shipping_city=addr["city"],
                    shipping_pincode=addr["pincode"],
                    total_price=round(total_price, 2),
                    payment_mode=random.choice(["Online", "Offline"]),
                    payment_status="Completed",
                    order_date=datetime.utcnow() - timedelta(days=random.randint(1, 90))
                )
                session.add(order)
                session.commit() # Commit to get order.id
                
                for item in items_in_order:
                    oi = OrderItem(
                        orderrecords_id=order.id, 
                        product_id=item["product"].id, 
                        quantity=item["quantity"], 
                        price_at_purchase=item["product"].price
                    )
                    session.add(oi)

                cust.no_of_purchases += 1 # Update purchase count
                session.add(cust)
                order_count += 1
        
        session.commit() # Commit all customer updates and order items
    print(f"Created {order_count} past orders.")

    print("--- 7. Creating Feedback ---")
    feedback_count = 0
    # Get all orders to create feedback
    with Session(engine) as session:
        all_order_items = session.exec(select(OrderItem)).all()
        # Create feedback for a sample of items
        for item in random.sample(all_order_items, min(len(all_order_items), 150)):
            order = session.get(OrderRecords, item.orderrecords_id)
            if order: # Ensure order exists
                add_feedback(
                    product_id=item.product_id,
                    customer_id=order.customer_id,
                    rating=random.randint(1, 5),
                    comment=random.choice(SAMPLE_COMMENTS)
                )
                feedback_count += 1
    print(f"Created {feedback_count} feedback entries.")

    print("--- 8. Creating Wholesale Orders ---")
    for i in range(20): # Create 20 wholesale orders
        items_in_order = []
        for _ in range(random.randint(2, 8)): # 2-8 product types per order
            items_in_order.append({
                "product": random.choice(products),
                "quantity": random.randint(10, 50) # Bulk quantities
            })
        
        retailer = random.choice(retailers)
        wholesaler = random.choice(wholesalers)
        
        add_wholesale_order(
            retailer_id=retailer.id,
            wholesaler_id=wholesaler.id,
            address=retailer.address,   
            items=items_in_order
        )
    print("Created 20 wholesale orders.")
    
    print("\n--- ✅ Database Seeding Complete! ---")


if __name__ == "__main__":
    seed()