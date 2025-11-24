# Project: Live MART- Online Delivery System 

## 🚀 Features

## 1. Multi-Role Architecture

Customer: Browse products, search/filter, add to cart, checkout, and track order history.

Retailer: Manage inventory (add/edit/delete products), view incoming orders, update order status, and view customer purchase history.

Wholesaler: Manage bulk supply and approve bulk orders from retailers.

## 2. Core Functionalities

Authentication: Secure Sign Up/Login with password hashing (SHA-256) and JWT Tokens.

Email Verification: OTP-based email verification required before login.

Smart Search: Real-time product filtering by Category, Price Range, and Name.

Order Management: Complete flow from "Pending" to "Shipped" to "Delivered".

Inventory Tracking: Stock levels automatically decrease upon purchase.

B2B Market: Retailers can restock their inventory by ordering from Wholesalers.

## 🛠️ Tech Stack

Backend: Python, FastAPI (Async), SQLModel (SQLAlchemy + Pydantic)

Database: SQLite (Auto-generated livemart.db)

Frontend: HTML5, CSS3 (Custom + Bootstrap), JavaScript (Fetch API)

Authentication: JWT (JSON Web Tokens), OAuth2

Email: FastAPI-Mail (SMTP)

## 📂 Project Structure

```
Live-MART/
├── backend/                  <-- Python & API Logic
│   ├── app/
│   │   ├── main.py           <-- Entry Point (API Routes)
│   │   ├── auth.py           <-- Auth Logic (JWT, Hashing, SMTP)
│   │   ├── database.py       <-- DB Connection & CRUD Functions
│   │   ├── db_models.py      <-- Database Tables (SQLModel)
│   │   ├── schemas.py        <-- Request/Response Validation
│   │   └── populate_*.py     <-- Data Seeders (Auto-fill DB)
│   │
│   ├── data/                 <-- Data Storage
│   │   ├── livemart.db       <-- Database File
│   │   └── product_images/   <-- Product Images (Downloaded by Seeder)
│
├── frontend/                 <-- User Interface
│   ├── index.html            <-- Landing Page
│   ├── dashboard.html        <-- Customer Shopping Page
│   ├── retailer-dashboard.html
│   ├── wholesaler-dashboard.html
│   ├── cart.html
│   ├── orders.html
│   └── ... (Auth & Detail pages)
│
└── README.md
```

### ⚙️ Setup & Installation

#### . Prerequisites

Python 3.9+

Pip

#### 2. Install Dependencies

Open a terminal in the root folder:

```
pip install requirements.txt
```

#### 3. Configure Environment (.env)

Create a .env file in backend/app/ (or update the hardcoded values in auth.py for testing):

```
SECRET_KEY="your-secret-key"
MAIL_USERNAME="your-email@gmail.com"
MAIL_PASSWORD="your-app-password"
MAIL_FROM="your-email@gmail.com"
MAIL_PORT=587
MAIL_SERVER="smtp.gmail.com"
```

#### 4. Seed the Database (Important!)

Populate the database with 500+ real products and images.

```
cd backend/app
python populate_db.py
```

This will create livemart.db, create Retailer ID 1, generate 200+ products, and download images to backend/data/product_images/.

5. Run the Server

```
# From backend/app/ directory
uvicorn main:app --reload
```

