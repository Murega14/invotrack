# Eripay

Eripay is a simple invoice management system built with Flask and SQLAlchemy. It allows users to manage customers, invoices, and payments.

## Getting Started

### Clone the Repository

```bash
git clone https://github.com/murega14/invotrack.git
cd invotrack 
```

### set up a virtual environment

```bash
python -m venv env
.\env\Scripts\activate
```

### Install Dependencies

```bash
pip install pipenv
pipenv install --dev
pipenv shell
```

### Environment Configuration

```env
FLASK_APP=app.py
FLASK_ENV=development
DATABASE_URI=sqlite:///dev_eripay.db
```

### Initialize the Database

```bash
flask db init
flask db migrate -m ""
flask db upgrade
```

### Run the Application

```bash
flask run
```
