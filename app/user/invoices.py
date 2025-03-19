from flask import Blueprint, request, jsonify
from ..models import db, Invoice, InvoiceItem, Business
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
        try:
            user_id = uuid.UUID(get_jwt_identity())
        except ValueError:
            return jsonify({"error": "invalid user ID format"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "no data provided"}), 400

        required_fields = ['business_id', 'due_date', 'items']
        if not all(field in data for field in required_fields):
            return jsonify({"error": f"missing required fields: {', '.join(required_fields)}"}), 400

        try:
            business_id = uuid.UUID(data['business_id'])
        except ValueError:
            return jsonify({"error": "invalid business ID format"}), 400

        invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"

        try:
            due_date = datetime.strptime(data['due_date'], '%d-%m-%Y')
        except ValueError:
            return jsonify({"error": "invalid date format. Use DD-MM-YYYY"}), 400
        try:
            new_invoice = Invoice(
                invoice_number=invoice_number,
                issuer_id=user_id,
                business_id=business_id,
                status='pending',
                total_amount=0,
                date_issued=datetime.now(),
                due_date=due_date
            )
            db.session.add(new_invoice)
            db.session.flush()
        except SQLAlchemyError as e:
            logger.error(f"failed to initialize invoice creation: {str(e)}")
            db.session.rollback()
            return jsonify({"message": "failed to initialize invoice creation", "error": str(e)}), 400

        total_amount = 0
        invoice_items = []

        items = data['items'] if isinstance(data['items'], list) else [data['items']]

        for item in items:
            if not isinstance(item, dict):
                db.session.rollback()
                return jsonify({"error": "invalid item format - must be an object"}), 400

            required_item_fields = ['description', 'quantity', 'unit_price']
            if not all(field in item for field in required_item_fields):
                db.session.rollback()
                missing = [f for f in required_item_fields if f not in item]
                return jsonify({"error": f"missing required fields in item: {', '.join(missing)}"}), 400

            if item['description'] is None or item['quantity'] is None or item['unit_price'] is None:
                db.session.rollback()
                return jsonify({"error": "description, quantity and unit_price cannot be null"}), 400

            try:
                try:
                    quantity = int(str(item['quantity']).strip().replace(',', ''))
                    if quantity <= 0:
                        raise ValueError("quantity must be greater than 0")
                except (ValueError, TypeError, AttributeError):
                    raise ValueError(f"invalid quantity value: {item['quantity']}")

                try:
                    unit_price = float(str(item['unit_price']).strip().replace(',', ''))
                    if unit_price <= 0:
                        raise ValueError("unit price must be greater than 0")
                except (ValueError, TypeError, AttributeError):
                    raise ValueError(f"invalid unit price value: {item['unit_price']}")

                try:
                    description = str(item['description']).strip()
                    if not description:
                        raise ValueError("description cannot be empty")
                except (ValueError, TypeError, AttributeError):
                    raise ValueError(f"invalid description value: {item['description']}")

                sub_total = quantity * unit_price

                logger.info(f"Processing item: description={description}, quantity={quantity}, unit_price={unit_price}, subtotal={sub_total}")

            except ValueError as e:
                db.session.rollback()
                return jsonify({"error": f"invalid item data: {str(e)}"}), 400

            invoice_item = InvoiceItem(
                invoice_id=new_invoice.id,
                description=description,
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
            return jsonify({"message": "failed to create invoice and add items", "error": str(e)}), 400

    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({"message": "internal server error", "error": str(e)}), 500
    
                  
@invoices.route('/api/v1/invoices', methods=['GET'])
@jwt_required()
def get_user_invoices():
    """
    Retrieve invoices associated with the current user.
    This function fetches the user ID from the JWT token, queries the database
    for invoices associated with that user, and returns the invoices in JSON format.
    If no invoices are found, it returns a 404 response with an appropriate message.
    In case of an error, it logs the error and returns a 500 response.
    Returns:
        tuple: A tuple containing a JSON response and an HTTP status code.
            - On success (200):
                {
                    "invoices": [
                        {
                            "id": int,
                            "invoice_number": str,
                            "recipient": str or None,
                            "amount": float,
                            "date_issued": str (ISO format),
                            "due_date": str (ISO format),
                            "status": str
                        },
                        ...
                    ]
                }
            - On failure (404):
                {
                    "message": "no invoices found associated with your user id"
                }
            - On error (500):
                {
                    "error": str
                }
    """
    try:
        user_id = uuid.UUID(get_jwt_identity())
        
        user_invoices = Invoice.query.filter_by(issuer_id=user_id).all()
        if not user_invoices:
            return jsonify({"message": "no invoices found associated with your user id"}), 404
        
        invoices_list = [{
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "recipient": invoice.business.name if invoice.business else None,
            "amount": float(invoice.total_amount),
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
        
@invoices.route('/api/v1/invoices/business/<uuid:business_id>', methods=['GET'])
@jwt_required()
def get_business_invoices(business_id):
    """
    Retrieve all invoices associated with a specific business.
    Args:
        business_id (uuid): The ID of the business whose invoices are to be retrieved.
    Returns:
        Response: A Flask Response object containing a JSON payload.
            - If invoices are found:
                - status code 200
                - JSON payload with "success" set to True and a list of invoices.
            - If no invoices are found:
                - status code 404
                - JSON payload with a message indicating no invoices were found.
            - If an error occurs:
                - status code 500
                - JSON payload with an error message and the error details.
    Each invoice in the list contains the following fields:
        - id (str): The invoice ID.
        - invoice_number (str): The invoice number.
        - issuer (str or None): The name of the issuer, if available.
        - amount (float): The amount of the invoice.
        - date_issued (str): The ISO formatted date when the invoice was issued.
        - due_date (str): The ISO formatted due date of the invoice.
        - status (str): The status of the invoice.
    """
    try:
        business_invoices = Invoice.query.filter_by(business_id=business_id).all()
        if not business_invoices:
            return jsonify({"message": "no invoices found associated with this business"}), 404
        
        invoices_list = [{
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "issuer": invoice.issuer.name if invoice.issuer else None,
            "amount": float(invoice.total_amount),
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
        

@invoices.route('/api/v1/invoices/received', methods=['GET'])
@jwt_required()
def get_received_invoices():
    """
    Retrieves all invoices received by the authenticated user's businesses.
    This function fetches all invoices where the user's businesses are recipients. It first gets all
    businesses owned by the authenticated user, then finds all invoices where these businesses are
    recipients.
    Returns:
        tuple: A tuple containing:
            - A JSON response with:
                - success (bool): True if operation was successful
                - invoices (list): List of dictionaries containing invoice details:
                    - id (UUID): Invoice unique identifier
                    - invoice_number (str): Invoice reference number
                    - issuer (str): Name of the business that issued the invoice
                    - recipient (str): Name of the business receiving the invoice
                    - amount (float): Total amount of the invoice
                    - status (str): Current status of the invoice
                    - date_issued (str): ISO formatted date when invoice was issued
                    - due_date (str): ISO formatted date when invoice is due
            - HTTP status code (int)
    Raises:
        500: If there's any error during the process
        404: If no businesses are associated with the user
    Requires:
        JWT authentication token in the request
    """
    try:
        user_id = uuid.UUID(get_jwt_identity())
        
        #retrieve all businesses related to the user
        businesses = Business.query.filter_by(owner_id=user_id).all()
        if not businesses:
            return jsonify({"message": "no businesses associated with this user"}), 404
        
        business_ids = [business.id for business in businesses]
        
        invoices = Invoice.query.filter(Invoice.business_id.in_(business_ids)).all()
        invoice_list = [{
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "issuer": invoice.issuer.name if invoice.issuer else None,
            "recipient": invoice.business.name if invoice.business else None,
            "amount": float(invoice.total_amount),
            "status": invoice.status,
            "date_issued": invoice.date_issued.isoformat(),
            "due_date": invoice.due_date.isoformat()
        } for invoice in invoices]
        
        response = jsonify({
            "success": True,
            "invoices": invoice_list
        })
        
        return response, 200
    
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "failed to fetch invoices",
            "error": str(e)
        }), 500
        
@invoices.route('/api/v1/invoices/<uuid:invoice_id>', methods=['GET'])
@jwt_required()
def get_single_invoice(invoice_id):
    """
    Retrieve a single invoice by its ID.
    Args:
        invoice_id (uuid): The ID of the invoice to retrieve.
    Returns:
        tuple: A tuple containing a JSON response and an HTTP status code.
            - On success (HTTP 200):
                {
                    "invoice": {
                        "id": str,
                        "invoice_number": str,
                        "issuer": str or None,
                        "recipient": str or None,
                        "details": [
                            {
                                "service": str,
                                "quantity": int,
                                "subtotal": float
                            },
                            ...
                        ],
                        "amount": float,
                        "date_issued": str (ISO format),
                        "due_date": str (ISO format),
                        "status": str
            - On failure (HTTP 500):
                {
                    "error": str
    Raises:
        Exception: If there is an error retrieving the invoice or its items.
    """
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        
        items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        invoice_items = [{
            "service": item.description,
            "quantity": item.quantity,
            "subtotal": float(item.subtotal)
        } for item in items]
        
        invoice_details = {
            "id": str(invoice_id),
            "invoice_number": invoice.invoice_number,
            "issuer": invoice.issuer.name if invoice.issuer else None,
            "recipient": invoice.business.name if invoice.business else None,
            "details": invoice_items,
            "amount": float(invoice.total_amount),
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
        
@invoices.route('/api/v1/invoices/<uuid:invoice_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_invoice(invoice_id):
    """
    Deletes an invoice by its ID.
    This function attempts to delete an invoice from the database. It first checks if the 
    invoice belongs to the currently authenticated user. If the user is not authorized to 
    delete the invoice, it returns a 403 error. If the invoice is successfully deleted, 
    it returns a success message. If there is a database error during the deletion process, 
    it rolls back the transaction and returns an error message. If any other exception 
    occurs, it returns a 500 internal server error.
    Args:
        invoice_id (uuid): The ID of the invoice to be deleted.
    Returns:
        Response: A JSON response indicating the result of the delete operation.
    """
    try:
        user_id = uuid.UUID(get_jwt_identity())
        
        invoice = Invoice.query.get_or_404(invoice_id)
        if invoice.issuer_id != user_id:
            return jsonify({"error": "unauthorized access"}), 403
        
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

@invoices.route('/api/v1/invoices/<uuid:invoice_id>/cancel', methods=['PATCH'])
@jwt_required()
def cancel_invoice(invoice_id):
    """
    Cancel an invoice by its ID.
    This function attempts to cancel an invoice by updating its status to 'cancelled'.
    It first checks if the current user is authorized to cancel the invoice.
    If the user is not authorized, it returns a 403 error.
    If the invoice is successfully canceled, it returns a success message with a 200 status code.
    If there is a database error during the cancellation process, it returns a 400 error with the error details.
    If any other exception occurs, it returns a 500 internal server error.
    Args:
        invoice_id (uuid): The ID of the invoice to be canceled.
    Returns:
        Response: A Flask response object containing a JSON message and an HTTP status code.
    """
    try:
        user_id = uuid.UUID(get_jwt_identity())
        invoice = Invoice.query.get_or_404(invoice_id)
        
        if invoice.issuer_id != user_id:
            return jsonify({"error": "unauthorized access"}), 403
        
        try:
            invoice.status = 'cancelled'
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "invoice has been cancelled"
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
    
@invoices.route('/api/v1/invoices/<uuid:invoice_id>/update', methods=['PUT'])
@jwt_required()
def update_invoice(invoice_id):
    """
    Update the details of an invoice with the given ID.
    Args:
        invoice_id (uuid): The ID of the invoice to be updated.
    Returns:
        Response: A JSON response indicating the success or failure of the update operation.
            - On success: Returns a JSON response with a success message and HTTP status code 200.
            - On failure: Returns a JSON response with an error message and appropriate HTTP status code.
                - If the invoice is not found: Returns a 404 status code.
                - If there is a database error: Returns a 400 status code.
                - If there is an internal server error: Returns a 500 status code.
    Raises:
        Exception: If there is an unexpected error during the execution of the function.
    """
    try:
        user_id = uuid.UUID(get_jwt_identity())
        
        invoice = Invoice.query.get_or_404(invoice_id)
        if not invoice:
            return jsonify({"error": "invoice not found"}), 404
        
        if invoice.issuer_id != user_id:
            return jsonify({"error": "unauthorized access"}), 403
        
        data = request.get_json()
        if not data or not data.get('items'):
            return jsonify({"error": "no data or no items provided"}), 400
        
        try:
            InvoiceItem.query.filter_by(invoice_id=invoice_id).delete()
            
            total_amount = 0
            items = data['items'] if isinstance(data['items'], list) else [data['items']]
            
            for item in items:
                if not isinstance(item, dict):
                    db.session.rollback()
                    return jsonify({"error": "invalid item format - must be an object"}), 400

                required_item_fields = ['description', 'quantity', 'unit_price']
                if not all(field in item for field in required_item_fields):
                    db.session.rollback()
                    missing = [f for f in required_item_fields if f not in item]
                    return jsonify({"error": f"missing required fields in item: {', '.join(missing)}"}), 400
                
                description = str(item['description']).strip()
                quantity = int(str(item['quantity']).strip().replace(',', ''))
                unit_price = float(str(item['unit_price']).strip().replace(',', ''))
                sub_total = quantity * unit_price
                
                invoice_item = InvoiceItem(
                    invoice_id=invoice_id,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=sub_total
                )
                
                db.session.add(invoice_item)
                total_amount += sub_total
            
            invoice.total_amount = total_amount
            
            if 'due_date' in data:
                try:
                    invoice.due_date = datetime.strptime(data['due_date'], '%d-%m-%Y')
                except ValueError:
                    return jsonify({"error": "invalid date format. Use DD-MM-YYYY"}), 400
            
                
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "invoice has been updated",
                "total_amount": float(total_amount)
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
 
@invoices.route('/api/v1/invoices/status/<string:status>', methods=['GET'])
@jwt_required()
def get_invoice_by_status(status: str):
    """
    Retrieve invoices by their status for the current authenticated user.
    Args:
        status (str): The status of the invoices to retrieve (e.g., 'paid', 'pending').
    Returns:
        Response: A JSON response containing a list of invoices with the specified status
                  for the current user, or an error message if no invoices are found or
                  an exception occurs.
    Raises:
        Exception: If an error occurs during the retrieval process, an error message is
                   logged and a JSON response with a 500 status code is returned.
    """
    try:
        user_id = uuid.UUID(get_jwt_identity())
        
        valid_statuses = ['pending', 'overdue', 'cancelled', 'paid']
        if status not in valid_statuses:
            return jsonify({"error": f"invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400
        
        invoices = Invoice.query.filter_by(status=status, issuer_id=user_id).all()
        
        if not invoices:
            return jsonify({"message": f"no {status} invoices available"}), 404
        
        invoices_list = [{
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "recipient": invoice.business.name if invoice.business else None,
            "amount": float(invoice.total_amount),
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
        
@invoices.route('/api/v1/invoices/business/<uuid:business_id>/status/<string:status>', methods=['GET'])
@jwt_required()
def get_business_invoices_by_status(business_id, status: str):
    """
    Retrieve invoices for a specific business based on their status.
    Args:
        business_id (uuid): The ID of the business whose invoices are to be retrieved.
        status (str): The status of the invoices to be retrieved (e.g., 'paid', 'pending').
    Returns:
        Response: A Flask JSON response containing:
            - success (bool): Indicates if the operation was successful.
            - invoices (list): A list of invoices with their details if found.
            - error (str): An error message if no invoices are found or an exception occurs.
            - message (str): A message indicating an internal server error if an exception occurs.
        HTTP Status Code:
            - 200: If invoices are found.
            - 404: If no invoices are found.
            - 500: If an internal server error occurs.
    """
    try:
        valid_statuses = ['pending', 'overdue', 'cancelled', 'paid']
        if status not in valid_statuses:
            return jsonify({"error": f"invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400
            
        invoices = Invoice.query.filter_by(status=status, business_id=business_id).all()
        if not invoices:
            return jsonify({"message": f"no {status} invoices found for this business"}), 404
        
        invoices_list = [{
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "issuer": invoice.issuer.name if invoice.issuer else None,
            "amount": float(invoice.total_amount),
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