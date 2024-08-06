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
        
        # Create sample users
        user1 = User(username='john_doe', name='John Doe', email='john@example.com')
        user1.set_password('password123')
        user2 = User(username='jane_smith', name='Jane Smith', email='jane@example.com')
        user2.set_password('password123')
        
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()
        
        # Create sample customers
        customer1 = Customer(name='Alice Johnson', email='alice@example.com')
        customer2 = Customer(name='Bob Brown', email='bob@example.com')
        
        db.session.add(customer1)
        db.session.add(customer2)
        db.session.commit()
        
        # Create sample invoices
        invoice1 = Invoice(
            customer_name=customer1.name,
            invoice_number=1001,
            amount=150.75,
            date_issued=datetime.strptime('2023-08-01', '%Y-%m-%d').date(),
            due_date=datetime.strptime('2023-08-15', '%Y-%m-%d').date(),
            status='unpaid'
        )
        
        invoice2 = Invoice(
            customer_name=customer2.name,
            invoice_number=1002,
            amount=250.00,
            date_issued=datetime.strptime('2023-07-15', '%Y-%m-%d').date(),
            due_date=datetime.strptime('2023-07-30', '%Y-%m-%d').date(),
            status='paid'
        )
        
        db.session.add(invoice1)
        db.session.add(invoice2)
        db.session.commit()
        
        # Create sample payments
        payment1 = Payment(
            invoice_number=invoice1.invoice_number,
            payment_method='credit_card',
            transaction_code = 'HA5FUJ9',
            amount=150.75
        )
        
        payment2 = Payment(
            invoice_number=invoice2.invoice_number,
            payment_method='bank_transfer',
            transaction_code = 'GAH56GF',
            amount=250.00
        )
        
        db.session.add(payment1)
        db.session.add(payment2)
        db.session.commit()
        
        print("Database populated successfully!")

if __name__ == '__main__':
    populate_data()
