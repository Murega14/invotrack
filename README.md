# Invotrack

Invotrack is a simple invoice management system built with Flask and SQLAlchemy. It allows users to manage customers, invoices, and payments.

## Features

- User authentication via Google OAuth
- Invoice management (create, view, update status)
- Customer registration and management  
- Payment processing via M-Pesa integration
- Automated invoice status updates and notifications
- Dashboard for business overview
- PDF invoice generation and download
- Responsive design using Tailwind CSS

## Tech Stack

- **Backend:** Python/Flask
- **Database:** SQLAlchemy/SQLite 
- **Authentication:** Google OAuth
- **Frontend:** HTML/Tailwind CSS
- **Payments:** M-Pesa API Integration
- **Task Scheduling:** Flask-APScheduler
- **Email:** Flask-Mail

## Setup

1. Clone the repository
2. Create a virtual environment:

```bash
python -m venv env
source env/bin/activate  # Linux/Mac
env\Scripts\activate     # Windows
```

## Installing Dependencies

```bash
pip install -r requirements.txt
```

## Set Up Environment Variables

```markdown
SECRET_KEY=your_secret_key
DEV_DATABASE_URI=sqlite:///your_db.sqlite
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_email_password
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
MPESA_CONSUMER_KEY=your_mpesa_key
MPESA_CONSUMER_SECRET=your_mpesa_secret
PASSKEY=your_mpesa_passkey
```

### Initialize Database

```bash
flask db upgrade
```

### Run Application

```bash
flask run
```

## Project Structure

```markdown
app/
├── __init__.py        # Application factory
├── models.py          # Database models
├── scheduler.py       # Background tasks
├── Routes/           
│   ├── authentication.py
│   ├── customers.py
│   ├── invoices.py
│   └── payments.py
├── templates/         # HTML templates
└── static/           # Static files
```

## Features in Detail

### Invoice Management

- Generate and track invoices
- Update payment status
- View invoice history
- Download invoices as PDF

### Payment Processing

- M-Pesa integration for mobile payments
- Multiple payment method support
- Real-time payment status updates
- Payment history tracking

### Customer Management

- Customer registration
- Customer profile management
- View customer payment history

### Automated Tasks

- Invoice status updates
- Payment due notifications
- Email reminders

## License

MIT License

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
