from io import BytesIO
import textwrap
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from api.models import CompanyInfo
from datetime import datetime

from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
import qrcode
from reportlab.lib.utils import ImageReader

def get_company_info():
    
    info = {}
    logo_obj = CompanyInfo.objects.filter(type='logo').first()
    phone_obj = CompanyInfo.objects.filter(type='phone').first()
    email_obj = CompanyInfo.objects.filter(type='email').first()
    address_obj = CompanyInfo.objects.filter(type='address').first()

    info['logo'] = logo_obj.logo_image.path if logo_obj and logo_obj.logo_image else None
    info['name'] = logo_obj.content if logo_obj and logo_obj.content else "BIL LTD"
    info['phone'] = phone_obj.content if phone_obj else ""
    info['email'] = email_obj.content if email_obj else ""
    info['address'] = address_obj.content if address_obj else ""
    return info

def generate_receipt_pdf(transaction):
    company_info = get_company_info()
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # WATERMARK 
    c.saveState()
    c.setFont("Helvetica-Bold", 50)
    c.setFillColorRGB(0.93, 0.93, 0.93)
    c.translate(width / 2, height / 2)
    c.rotate(45)
    text_width = c.stringWidth(company_info["name"], "Helvetica-Bold", 50)
    c.drawString(-text_width / 2, 0, company_info["name"])
    c.restoreState()

    # HEADER 
    header_y = height - 50
    
    # Company Logo
    if company_info["logo"]:
        try:
            c.drawImage(company_info["logo"], 40, header_y - 60, width=90, height=45,
                        preserveAspectRatio=True, mask="auto")
        except:
            pass

    # Company Name
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.HexColor("#008080"))
    c.drawString(150, header_y - 30, company_info["name"])
    
    # Header Line
    c.setStrokeColor(colors.HexColor("#008080"))
    c.setLineWidth(2)
    c.line(40, header_y - 65, width - 40, header_y - 65)

    # RECEIPT TITLE 
    title_y = header_y - 90
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#008080"))
    c.drawString(40, title_y, "Payment Receipt")
    
    # Date and Reference
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawRightString(width - 40, title_y, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    c.drawRightString(width - 40, title_y - 15, f"Ref: {transaction.transaction_reference}")

    # TABLE CONTAINER 
    table_top = title_y - 40
    table_bottom = 250  # Increased to make more space
    table_left = 40
    table_right = width - 40

    # Main table border
    c.setStrokeColor(colors.HexColor("#008080"))
    c.setFillColor(colors.HexColor("#F8FDFC"))
    c.roundRect(table_left, table_bottom, table_right - table_left, table_top - table_bottom, 8, stroke=1, fill=1)

    # TABLE CONTENT 
    confirmed_by_name = transaction.confirmed_by.fullname if transaction.confirmed_by else "N/A"

    rows = [
        ("Sender", transaction.sender_name or "N/A"),
        ("Receiver", transaction.receiver_name or "N/A"),
        ("Receiver Contact", transaction.receiver_contact or "N/A"),
        ("Total Amount", f"{transaction.amount:,.2f}"),
        ("Currency", transaction.currency or "N/A"),
        ("Country", transaction.proof.country.name if hasattr(transaction.proof, 'country') and transaction.proof.country else "N/A"),
        ("Charge Deducted", f"{transaction.charge_amount:,.2f}"),
        ("Client Receives", f"{transaction.net_amount:,.2f}"),
        ("Confirmed By", confirmed_by_name),  
    ]

    # Calculate row positioning
    num_rows = len(rows)
    available_height = table_top - table_bottom - 20
    row_height = available_height / num_rows
    
    # Vertical divider position
    divider_x = table_left + (table_right - table_left) * 0.4

    # Draw rows
    current_y = table_top - 20
    
    for i, (label, value) in enumerate(rows):
        # Label (left side)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#2E4A4A"))
        c.drawString(table_left + 15, current_y - 5, f"{label}:")
        
        # Value (right side)
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        
        # Special formatting for amount fields
        if "Amount" in label or "Charge" in label or "Receives" in label:
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.HexColor("#008080"))
        
        c.drawString(divider_x + 10, current_y - 5, str(value))
        
        # Draw horizontal dotted line (except after last row)
        if i < len(rows) - 1:
            c.setStrokeColor(colors.HexColor("#C0C0C0"))
            c.setLineWidth(0.3)
            c.setDash([2, 2])
            c.line(table_left + 10, current_y - 15, table_right - 10, current_y - 15)
            c.setDash()
        
        current_y -= row_height

    # Draw vertical dotted divider
    c.setStrokeColor(colors.HexColor("#C0C0C0"))
    c.setLineWidth(0.3)
    c.setDash([2, 2])
    c.line(divider_x, table_bottom + 10, divider_x, table_top - 10)
    c.setDash()

    # SIGNATURE SECTION - MOVED TO BETTER POSITION
    signature_y = table_bottom - 80  # Positioned below the table
    
    # Signature container with background
    c.setFillColor(colors.HexColor("#FFFFFF"))
    c.roundRect(table_left, signature_y - 40, 250, 50, 5, fill=1, stroke=1)
    c.setStrokeColor(colors.HexColor("#008080"))
    c.setLineWidth(0.5)
    c.roundRect(table_left, signature_y - 40, 250, 50, 5, stroke=1, fill=0)
    
    # Signature line
    signature_line_y = signature_y - 15
    c.setStrokeColor(colors.HexColor("#666666"))
    c.setLineWidth(1)
    c.line(table_left + 10, signature_line_y, table_left + 200, signature_line_y)
    
    # Signature label
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#424242"))
    signature_text = f"Authorized Signature: {confirmed_by_name}"
    c.drawString(table_left + 10, signature_y - 30, signature_text)
    
    # Verification text
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#757575"))
    c.drawString(table_left + 10, signature_y - 45, "Digitally verified and approved")

    # QR CODE SECTION - MOVED TO RIGHT SIDE
    qr_bottom = signature_y - 50  # Position QR below signature
    qr_left = table_right - 130
    
    # QR Code background
    c.setFillColor(colors.HexColor("#E0F2F1"))
    c.roundRect(qr_left, qr_bottom, 100, 100, 5, fill=1, stroke=0)
    
    # Generate QR code
    try:
        import qrcode
        from reportlab.lib.utils import ImageReader
        
        qr_data = f"""TEXT:
        REF: {transaction.transaction_reference}
        AMOUNT: {transaction.amount} {transaction.currency}
        SENDER: {transaction.sender_name}
        RECEIVER: {transaction.receiver_name}
        DATE: {datetime.now().strftime('%Y-%m-%d')}
        """.strip()
        
        qr_img = qrcode.make(qr_data)
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        
        c.drawImage(ImageReader(qr_buffer), qr_left + 10, qr_bottom + 10, 
                   width=80, height=80, mask='auto')
        
        # QR code label
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#008080"))
        c.drawString(qr_left + 25, qr_bottom - 10, "VERIFICATION QR CODE")
        
    except ImportError:
        # Fallback if QR code library is not available
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.red)
        c.drawString(qr_left + 10, qr_bottom + 40, "QR Code requires:")
        c.drawString(qr_left + 10, qr_bottom + 25, "pip install qrcode[pil]")

    # ALTERNATIVE DISPLAY IF NO CONFIRMATION 
    if confirmed_by_name == "N/A":
        # Add system authorization note below signature
        system_auth_y = signature_y - 80
        c.setFillColor(colors.HexColor("#FFF3E0"))
        c.roundRect(table_left, system_auth_y - 25, 250, 30, 5, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#FF6B35"))
        c.setLineWidth(0.5)
        c.roundRect(table_left, system_auth_y - 25, 250, 30, 5, stroke=1, fill=0)
        
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#FF6B35"))
        c.drawString(table_left + 10, system_auth_y - 10, "System Authorized")
        
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#757575"))
        c.drawString(table_left + 10, system_auth_y - 20, "Automatically processed and verified")

    # COMPANY CONTACT FOOTER 
    footer_y = 100  # Increased footer space
    
    # Footer background
    c.setFillColor(colors.HexColor("#F5F5F5"))
    c.rect(0, 0, width, footer_y, fill=1, stroke=0)
    
    # Contact information
    contact_y = 80
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#008080"))
    c.drawString(40, contact_y, "Contact Information:")
    
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#424242"))
    
    if company_info['email']:
        c.drawString(40, contact_y - 15, f"📧 {company_info['email']}")
    if company_info['phone']:
        c.drawString(40, contact_y - 30, f"📞 {company_info['phone']}")
    if company_info['address']:
        # Handle long addresses
        address_lines = textwrap.wrap(company_info['address'], width=50)
        for i, line in enumerate(address_lines):
            c.drawString(40, contact_y - 45 - (i * 12), f"📍 {line}")

    # FINAL MESSAGE 
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.HexColor("#008080"))
    c.drawCentredString(width / 2, 40, f"Thank you for choosing {company_info['name']}!")
    
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#757575"))
    c.drawCentredString(width / 2, 25, "We appreciate your support and trust in our services")

    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def send_receipt_email(transaction, pdf_bytes):
    recipient_email = transaction.proof.receiver_email or transaction.user.email

    if not recipient_email:
        print("No recipient email provided. Cannot send receipt.")
        return False

    try:
        validate_email(recipient_email)
    except ValidationError:
        print(f"Invalid email address: {recipient_email}")
        return False

    # Enhanced email content
    email_subject = f'Payment Receipt - {transaction.transaction_reference}'
    email_body = f"""
Dear {transaction.sender_name},

Your payment has been successfully processed and delivered. 

Transaction Details:
- Reference: {transaction.transaction_reference}
- Amount: {transaction.currency} {transaction.amount:.2f}
- Receiver: {transaction.receiver_name}
- Date: {datetime.now().strftime('%B %d, %Y %I:%M %p')}

Please find your detailed receipt attached with this email.

If you have any questions about this transaction, please don't hesitate to contact us.

Best regards,
{get_company_info()['name']} Team
"""

    email = EmailMessage(
        subject=email_subject,
        body=email_body,
        to=[recipient_email]
    )

    email.attach(f'receipt_{transaction.transaction_reference}.pdf', pdf_bytes, 'application/pdf')

    try:
        email.send()
        print(f"✓ Receipt successfully sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"✗ Failed to send email: {e}")
        return False