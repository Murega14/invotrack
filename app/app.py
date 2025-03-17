from app import create_app
from flask import render_template, session, flash, redirect, jsonify
from.models import *
from sqlalchemy import func
from flask_jwt_extended import get_jwt_identity, jwt_required
from uuid import UUID

app = create_app()

@app.route("/")
def index():
    response = jsonify({"message": "Documentation coming soon"})
    return response, 200

@app.route('/dashboard')
@jwt_required()
def dashboard():
    user_id = UUID(get_jwt_identity())
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    user_invoices = Invoice.query.filter_by(user_id=user.id).all()
    
    outstanding_invoices = Invoice.query.filter(Invoice.issuer_id == user.id, Invoice.status != 'paid').count()
    total_paid = db.session.query(func.sum(Invoice.total_amount)).filter(Invoice.issuer_id == user.id, Invoice.status == 'paid').scalar() or 0
    total_unpaid = db.session.query(func.sum(Invoice.total_amount)).filter(Invoice.issuer_id == user.id, Invoice.status != 'paid').scalar() or 0
    
    response = jsonify({
        "success": True,
        "outstanding_invoices": outstanding_invoices,
        "total_paid": total_paid,
        "total_unpaid": total_unpaid
    })
    return response, 200


if __name__ == "__main__":
    app.run(debug=True)
