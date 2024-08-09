from app.app import app  # Import the app object correctly
from app.models import db, User, Customer, Invoice, Payment
from datetime import datetime

def populate_data():
    with app.app_context():
        # Clear existing data
        db.session.query(User).delete()
        db.session.query(Customer).delete()
        db.session.query(Invoice).delete()
        db.session.query(Payment).delete()
        db.session.commit()
        
        
        print("Database populated successfully!")

if __name__ == '__main__':
    populate_data()
