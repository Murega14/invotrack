from flask_admin.contrib.sqla import ModelView
from.models import *

class UserAdmin(ModelView):
    column_list = ('name', 'email')
    column_labels = {'name': 'Name', 'email': 'Email'}
    column_filters = ('name', 'email')
    
class InvoiceAdmin(ModelView):
    column_list = ('user_id', 'invoice_number', 'customer_name', 'amount', 'date_issued', 'due_date', 'status')
    column_labels = {
        'user_id': 'UserId',
        'invoice_number': 'Invoice Number',
        "customer_name": 'Customer Name',
        'amount': 'Amount',
        'date_issued': 'Date Issued',
        'due_date': 'Due Date',
        'status': 'Status'
    }
    column_filters = ('invoice_number', 'customer_name', 'date_issued', 'due_date')
    
