from datetime import datetime, timedelta
from flask_mail import Message
from . import db, mail, scheduler

def init_scheduler(app):
    def update_invoice_status():
        """Update overdue invoices."""
        try:
            from .models import Invoice 
            now = datetime.now().date()
            overdue_invoices = Invoice.query.filter(
                Invoice.due_date < now,
                Invoice.status == 'unpaid'
            ).all()
            
            for invoice in overdue_invoices:
                invoice.status = 'overdue'
                
            db.session.commit()
            app.logger.info(f"Updated {len(overdue_invoices)} overdue invoices")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating invoice status: {str(e)}")

    def send_due_notifications():
        """Send notifications for invoices due soon."""
        try:
            from .models import Invoice
            
            now = datetime.now().date()
            due_invoices = Invoice.query.filter(
                Invoice.due_date >= now,
                Invoice.due_date <= now + timedelta(days=3),
                Invoice.status == 'unpaid'
            ).all()
            
            for invoice in due_invoices:
                message = Message(
                    subject="Invoice Due Reminder",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[invoice.user.email]
                )
                message.body = f"""
                Dear {invoice.user.name},
                
                This is a reminder that your invoice {invoice.invoice_number} 
                is due on {invoice.due_date}.
                
                Amount Due: ${invoice.amount:,.2f}
                
                Please ensure timely payment to avoid late fees.
                
                Best regards,
                Your Business Name
                """
                mail.send(message)
                app.logger.info(f"Sent reminder for invoice {invoice.invoice_number}")
        except Exception as e:
            app.logger.error(f"Error sending notifications: {str(e)}")

    with app.app_context():
        scheduler.add_job(
            id='update_overdue_invoices',
            func=update_invoice_status,
            trigger='cron',
            hour=0,
            minute=0,
            replace_existing=True
        )
        
        scheduler.add_job(
            id='send_due_invoice_notifications',
            func=send_due_notifications,
            trigger='cron',
            hour=20,
            minute=30,
            replace_existing=True
        )
        
        scheduler.start()