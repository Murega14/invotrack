from app import create_app
from flask import render_template, session, flash, redirect, jsonify
from.models import *
from sqlalchemy import func

app = create_app()

@app.route("/")
def index():
    response = jsonify({"message": "Documentation coming soon"})
    return response, 200

@app.route('/dashboard')
def dashboard():
    google_id = session.get('google_id')
    
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        flash('user not found')
        return redirect('/login') 
    user_invoices = Invoice.query.filter_by(user_id=user.id).all()
    
    outstanding_invoices = Invoice.query.filter(Invoice.user_id == user.id, Invoice.status != 'paid').count()
    total_paid = db.session.query(func.sum(Invoice.amount)).filter(Invoice.user_id == user.id, Invoice.status == 'paid').scalar() or 0
    total_unpaid = db.session.query(func.sum(Invoice.amount)).filter(Invoice.user_id == user.id, Invoice.status != 'paid').scalar() or 0
    
    return render_template('dashboard.html',
                           outstanding_invoices=outstanding_invoices, 
                           total_paid="{:,.2f}".format(total_paid),
                           total_unpaid="{:,.2f}".format(total_unpaid),
                           user_invoices=user_invoices)


if __name__ == "__main__":
    app.run(debug=True)
