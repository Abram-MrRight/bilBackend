# api/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Proof, Transaction
from .utils import generate_receipt_pdf, send_transaction_receipt_email
import uuid

@receiver(post_save, sender=Proof)
def create_transaction_on_final_status(sender, instance, created, **kwargs):
    if not created and instance.status == 'money_delivered':
        if not hasattr(instance, 'transaction'):
            transaction = Transaction.objects.create(
                proof=instance,
                user=instance.user,
                sender_name=instance.sender_name,
                receiver_name=instance.receiver_name or "N/A",
                receiver_contact=instance.receiver_contact or "N/A",
                amount=instance.amount,
                currency=instance.currency,
                transaction_reference=str(uuid.uuid4()).split('-')[0],
                confirmed_by=instance.updated_by if hasattr(instance, 'updated_by') else None,
            )

            # Generate PDF receipt
            receipt_path = generate_receipt_pdf(transaction)
            transaction.receipt_file = receipt_path
            transaction.save()

            # Send email
            send_transaction_receipt_email(transaction.user.email, transaction)
