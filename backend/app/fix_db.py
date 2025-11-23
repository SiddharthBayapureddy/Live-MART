from sqlmodel import Session, delete
from database import engine
from db_models import Customer, Retailer, Wholesaler

def clear_users():
    with Session(engine) as session:
        # Construct delete statements for each user type
        session.exec(delete(Customer))
        session.exec(delete(Retailer))
        session.exec(delete(Wholesaler))
        
        session.commit()
        print("All user accounts have been cleared.")

if __name__ == "__main__":
    clear_users()