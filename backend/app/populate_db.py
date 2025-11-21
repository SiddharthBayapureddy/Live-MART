import os
import random
import requests # pip install requests
from sqlmodel import Session, select, delete
from db_models import Product, Category, Retailer
from database import engine, create_db_and_tables, add_retailer, add_category, add_product
from auth import hash_password

# --- CONFIGURATION ---
RETAILER_ID = 1
IMAGE_DIR = "../data/product_images"
ITEMS_PER_CATEGORY = 40  # Updated to 40

# --- CATEGORY MAPPING ---
CATEGORY_IDS = {
    "Electronics": 1,
    "Groceries": 2,
    "Fashion": 3,
    "Books": 5,
    "Home": 7,
    "Sports": 8
}

# --- GENERATION POOLS ---
POOLS = {
    "Electronics": {
        "brands": ["Sony", "Samsung", "Apple", "Dell", "HP", "Logitech", "Bose", "Canon", "Nikon", "Asus", "OnePlus", "Google", "LG", "Microsoft", "Razer"],
        "nouns": ["Headphones", "Smart TV", "Laptop", "Speaker", "Smartphone", "Keyboard", "Mouse", "Camera", "Tablet", "Smart Watch", "Monitor", "Earbuds", "Drone", "Console"],
        "adjectives": ["Wireless", "4K", "Gaming", "Bluetooth", "Pro", "Ultra", "Mini", "Smart", "Noise-Cancelling", "Portable"]
    },
    "Groceries": {
        "brands": ["Nestle", "Kellogg's", "Heinz", "Coca-Cola", "Pepsi", "Lays", "Quaker", "Tropicana", "Tata", "Britannia", "Amul", "Dabur", "Cadbury", "Kissan"],
        "nouns": ["Coffee", "Tea", "Cereal", "Olive Oil", "Chocolate", "Chips", "Pasta", "Rice", "Almonds", "Honey", "Juice", "Butter", "Oats", "Jam", "Sauce"],
        "adjectives": ["Organic", "Fresh", "Premium", "Dark", "Whole Wheat", "Basmati", "Natural", "Instant", "Salted", "Spicy"]
    },
    "Fashion": {
        "brands": ["Nike", "Adidas", "Zara", "H&M", "Gucci", "Levi's", "Uniqlo", "Puma", "Calvin Klein", "Ralph Lauren", "Tommy Hilfiger", "Vans", "Converse"],
        "nouns": ["T-Shirt", "Jeans", "Shoes", "Jacket", "Hoodie", "Dress", "Sunglasses", "Watch", "Backpack", "Cap", "Boots", "Belt", "Sneakers", "Shirt"],
        "adjectives": ["Cotton", "Slim Fit", "Running", "Leather", "Oversized", "Classic", "Denim", "Casual", "Formal", "Printed"]
    },
    "Books": {
        "brands": ["Penguin", "HarperCollins", "Oxford", "Pearson", "Scholastic", "Marvel", "DC", "Lonely Planet", "Vintage", "Bloomsbury"],
        "nouns": ["Novel", "Guide", "Textbook", "Biography", "Comic", "Cookbook", "Encyclopedia", "Atlas", "Journal", "Thriller", "Mystery", "Dictionary"],
        "adjectives": ["Hardcover", "Paperback", "Illustrated", "Classic", "Bestselling", "Limited Edition", "Complete", "Modern", "Essential"]
    },
    "Home": {
        "brands": ["IKEA", "Philips", "Dyson", "KitchenAid", "Prestige", "Samsung", "LG", "Milton", "Tupperware", "Duracell", "Bajaj", "Havells", "Sleepwell"],
        "nouns": ["Blender", "Toaster", "Coffee Maker", "Air Fryer", "Lamp", "Bedsheet", "Pillow", "Bottle", "Vacuum", "Plant", "Cooker", "Fan", "Safe", "Iron"],
        "adjectives": ["Smart", "LED", "Cotton", "Memory Foam", "Steel", "Glass", "Automatic", "Electric", "Decorative", "Compact"]
    },
    "Sports": {
        "brands": ["Decathlon", "Wilson", "Spalding", "Yonex", "Under Armour", "Reebok", "Garmin", "Speedo", "Nivia", "Cosco", "Adidas", "Puma"],
        "nouns": ["Yoga Mat", "Dumbbells", "Football", "Racket", "Gym Bag", "Helmet", "Treadmill", "Tent", "Goggles", "Bat", "Gloves", "Jersey", "Shoes"],
        "adjectives": ["Pro", "Training", "Heavy", "Lightweight", "Waterproof", "Adjustable", "Professional", "Durable", "Size 5", "Graphite"]
    }
}

# --- DOWNLOAD HELPER ---
def download_image(product_id, text_label):
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
    
    path = os.path.join(IMAGE_DIR, f"{product_id}.jpg")
    if os.path.exists(path):
        return # Skip existing

    # Placeholder service: Dark Background, Neon Blue Text
    safe_text = text_label.replace(" ", "+")
    url = f"https://placehold.co/600x400/1a1a1a/00f3ff.jpg?text={safe_text}&font=montserrat"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(path, 'wb') as f:
                f.write(response.content)
    except Exception as e:
        print(f"Error downloading {text_label}: {e}")

def get_category_url(text):
    safe_text = text.replace(" ", "+")
    return f"https://placehold.co/600x400/1a1a1a/00f3ff.jpg?text={safe_text}"

# --- MAIN SEEDER ---
def seed_manual_db():
    print(f"--- Starting {ITEMS_PER_CATEGORY * 6} Product Seeding (40 per category) ---")
    create_db_and_tables()
    
    # 1. Clear Old Products
    print("Clearing old products...")
    with Session(engine) as session:
        session.exec(delete(Product))
        session.commit()
        
    # 2. Ensure Categories
    print("Ensuring Categories exist...")
    for name, cat_id in CATEGORY_IDS.items():
        cat_img = get_category_url(name)
        with Session(engine) as session:
            existing = session.get(Category, cat_id)
            if not existing:
                new_cat = Category(id=cat_id, name=name, description=f"All {name}", image_url=cat_img)
                session.add(new_cat)
                session.commit()
            else:
                if existing.name != name:
                    existing.name = name
                    session.add(existing)
                    session.commit()

    # 3. Ensure Retailer
    with Session(engine) as session:
        retailer = session.get(Retailer, RETAILER_ID)
        if not retailer:
            print("Creating Retailer ID 1...")
            retailer = add_retailer(
                name="Super Retailer", mail="admin@shop.com", hashed_password=hash_password("admin123"),
                business_name="Live Mart Official", address="123 Main St", city="Hyderabad", state="Telangana", pincode="500001"
            )

    # 4. Generate Products
    total_created = 0
    
    for cat_name, pool in POOLS.items():
        cat_id = CATEGORY_IDS[cat_name]
        print(f"Generating {ITEMS_PER_CATEGORY} items for {cat_name} (ID: {cat_id})...")
        
        generated_names = set()
        attempts = 0
        
        while len(generated_names) < ITEMS_PER_CATEGORY:
            attempts += 1
            if attempts > 1000: break 
            
            brand = random.choice(pool["brands"])
            noun = random.choice(pool["nouns"])
            adj = random.choice(pool["adjectives"])
            
            if random.random() > 0.5:
                name = f"{brand} {adj} {noun}"
            else:
                name = f"{adj} {brand} {noun}"
            
            if name in generated_names:
                name = f"{name} {random.randint(100, 999)}"
            
            generated_names.add(name)
            
            if cat_name == "Electronics": price = round(random.uniform(2000, 80000), 2)
            elif cat_name == "Fashion": price = round(random.uniform(500, 5000), 2)
            elif cat_name == "Groceries": price = round(random.uniform(50, 800), 2)
            elif cat_name == "Books": price = round(random.uniform(200, 1500), 2)
            elif cat_name == "Home": price = round(random.uniform(500, 10000), 2)
            else: price = round(random.uniform(300, 5000), 2) 
            
            stock = 0 if random.random() < 0.08 else random.randint(5, 150)
            
            with Session(engine) as session:
                p = Product(
                    name=name,
                    description=f"High quality {name} in {cat_name} category.",
                    category_id=cat_id,
                    price=price,
                    stock=stock,
                    retailer_id=RETAILER_ID,
                    image_url="" 
                )
                session.add(p)
                session.commit()
                session.refresh(p)
                
                p.image_url = f"product_images/{p.id}.jpg"
                session.add(p)
                session.commit()
                
                download_image(p.id, name)
                
            total_created += 1
            if total_created % 20 == 0:
                print(f" - Created {total_created} products total...")

    print(f"\n--- ✅ Success! Created {total_created} Products across 6 Categories. ---")

if __name__ == "__main__":
    seed_manual_db()