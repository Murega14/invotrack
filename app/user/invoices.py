from flask import Blueprint, request, jsonify
from ..models import db, Invoice, InvoiceItem
from ..extensions import logger
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import uuid

invoices = Blueprint('invoices', __name__)

@invoices.route('/api/v1/invoices/create', methods=['POST'])
@jwt_required()        
def create_invoice():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not all([data.get('business_id'), data.get('due_date'), data.get('items')]):
            return jsonify({"error": "input data is required"}), 400
        
        
        invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        
        try:
            new_invoice = Invoice(
                invoice_number=invoice_number,
                issuer_id=user_id,
                business_id=data['business_id'],
                status='pending',
                total_amount=0,
                date_issued=datetime.now(),
                due_date=datetime.strptime(data['due_date'], '%d-%m-%Y')
            )
            db.session.add(new_invoice)
            db.session.flush()
            
        except SQLAlchemyError as e:
            logger.error(f"failed to initialize invoice creation: {str(e)}")
            db.session.rollback()
            return jsonify({
                "message": "failed to initialize invoice creation",
                "error": str(e)
            }), 400
            
        total_amount = 0
        invoice_items = []
        
        for item in data['items']:
            if not all([item.get('descrption'), item.get('quantity'), item.get('unit_price')]):
                return jsonify({
                    "message": "invalid item data",
                    "error": "description, quantity and unit_price are required for each item"
                }), 400

            quantity = int(item['quantity'])
            unit_price = float(item['unit_price'])
            sub_total = quantity * unit_price
            
            invoice_item = InvoiceItem(
                invoice_id=new_invoice.id,
                description=item['description'],
                quantity=quantity,
                unit_price=unit_price,
                subtotal=sub_total
            )
            invoice_items.append(invoice_item)
            total_amount += sub_total
        
        new_invoice.total_amount = total_amount
        
        try:
            db.session.add_all(invoice_items)
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "invoice created successfully",
                "invoice_id": str(new_invoice.id),
                "invoice_number": invoice_number,
                "total_amount": float(total_amount)
            }), 201
            
        except SQLAlchemyError as e:
            logger.error(f"failed to commit invoice creation: {str(e)}")
            db.session.rollback()
            return jsonify({
                "message": "failed to create invoice and add items",
                "error": str(e)
            }), 400
            
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500
                               
@invoices.route('/api/v1/invoices', methods=['GET'])
@jwt_required()
def get_user_invoices():
    try:
        user_id = get_jwt_identity()
        
        user_invoices = Invoice.query.filter_by(owner_id=user_id).all()
        if not user_invoices:
            return jsonify({"message": "no invoices found associated with your user id"}), 404
        
        invoices_list =[{
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "recipient": invoice.business.name if invoice.business else None,
            "amount": float(invoice.amount),
            "date_issued": invoice.date_issued.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "status": invoice.status
        } for invoice in user_invoices]
        
        return jsonify({
            "success": True,
            "invoices": invoices_list
        }), 200
        
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500
        
@invoices.route('/api/v1/invoices/<int:business_id>',methods=['GET'])
@jwt_required()
def get_business_invoices(business_id: int):
    try:
        business_invoices = Invoice.query.filter_by(business_id=business_id).all()
        if not business_invoices:
            return jsonify({"message": "no invoices found associated with this business"}), 404
        
        invoices_list = [{
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "issuer": invoice.issuer.name if invoice.issuer else None,
            "amount": float(invoice.amount),
            "date_issued": invoice.date_issued.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "status": invoice.status
        } for invoice in business_invoices]
        
        return jsonify({
            "success": True,
            "invoices": invoices_list
        }), 200
        
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500
        
@invoices.route('/api/v1/invoices/<int:id>', methods=['GET'])
@jwt_required()
def get_single_invoice(id: int):
    try:
        invoice = Invoice.query.get_or_404(id)
        
        items = InvoiceItem.query.filter_by(invoice_id=id).all()
        invoice_items = [{
            "service": item.description,
            "quantity": item.quantity,
            "subtotal": float(item.subtotal)
        } for item in items]
        
        invoice_details = {
            "id": id,
            "invoice_number": invoice.invoice_number,
            "issuer": invoice.issuer.name if invoice.issuer else None,
            "recipient": invoice.business.name if invoice.business else None,
            "details": invoice_items,
            "amount": float(invoice.amount),
            "date_issued": invoice.date_issued.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "status": invoice.status
        }
        
        return jsonify({
            "success": True,
            "invoice": invoice_details
        }), 200
        
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500
        
@invoices.route('/api/v1/invoices/<int:id>/delete', methods=['DELETE'])
@jwt_required()
def delete_invoice(id: int):
    try:
        user_id = get_jwt_identity()
        
        invoice = Invoice.query.get_or_404(id)
        if invoice.owner_id != user_id:
            return jsonify({"Error": "unauthorized access"})
        
        try:
            db.session.delete(invoice)
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "deleted invoice successfully"
            }), 200
        
        except SQLAlchemyError as e:
            logger.error(f"database error: {str(e)}")
            db.session.rollback()
            return jsonify({
                "message": "failed to delete invoice",
                "error": str(e)
            }), 400
            
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500       

@invoices.route('/api/v1/invoices/<int:id>/cancel', methods=['PATCH'])
@jwt_required()
def cancel_invoice(id: int):
    try:
        user_id = get_jwt_identity()
        invoice = Invoice.query.get_or_404(id)
        
        if invoice.owner_id != user_id:
            return jsonify({"error": "unauthorized access"}), 403
        
        try:
            invoice.status = 'canceled'
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "invoice has been canceled"
            }), 200
        
        except SQLAlchemyError as e:
            logger.error(f"database error: {str(e)}")
            db.session.rollback()
            return jsonify({
                "message": "failed to cancel invoice",
                "error": str(e)
            }), 400
            
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500
    
@invoices.route('/api/v1/invoices/<int:id>/update', methods=['PUT'])
@jwt_required()
def update_invoice(id: int):
    try:
        user_id = get_jwt_identity()
        
        invoice = InvoiceItem.query.filter_by(invoice_id=id).first()
        if not invoice:
            return jsonify({"error": "invoice not found"}), 404
        
        data = request.get_json()
        
        try:
            if 'description' in data:
                invoice.description = data['description']
            if 'quantity' in data:
                invoice.quantity = int(data['quantity'])
            if 'unit_price' in data:
                invoice.unit_price = float(data['unit_price'])
                
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "invoice details have been updated"
            }), 200
            
        except SQLAlchemyError as e:
            logger.error(f"database error: {str(e)}")
            db.session.rollback()
            return jsonify({
                "message": "failed to update invoice details",
                "error": str(e)
            }), 400
            
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500
 
@invoices.route('/api/v1/invoices/<string:status>', methods=['GET'])
@jwt_required()
def get_invoice_by_status(status: str):
    try:
        user_id = get_jwt_identity()
        invoices = Invoice.query.filter_by(status=status, owner_id=user_id).all()
        
        if not invoices:
            return jsonify({"error": f"no {status} invoices available"})
        
        invoices_list = [{
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "recipient": invoice.business.name if invoice.business else None,
            "amount": float(invoice.amount),
            "date_issued": invoice.date_issued.isoformat(),
            "due_date": invoice.due_date.isoformat()
        } for invoice in invoices]
        
        return jsonify({
            "success": True,
            "invoices": invoices_list
        }), 200
        
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500
        
@invoices.route('api/v1/invoices/<int:business_id>/<string:status>', methods=['GET'])
@jwt_required()
def get_business_invoices_by_status(business_id: int, status: str):
    try:
        invoices = Invoice.query.filter_by(status=status, business_id=business_id).all()
        if not invoices:
            return jsonify({"error": f"no {status} invoices found"}), 404
        
        invoices_list = [{
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "issuer": invoice.issuer.name if invoice.issuer else None,
            "amount": float(invoice.amount),
            "date_issued": invoice.date_issued.isoformat(),
            "due_date": invoice.due_date.isoformat()
        } for invoice in invoices]
        
        return jsonify({
            "success": True,
            "invoices": invoices_list
        }), 200
        
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500