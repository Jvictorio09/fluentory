"""
Certificate Generation Utilities
Functions to create and generate certificates with QR codes
"""
import os
from django.conf import settings
from django.utils import timezone
from django.core.files import File
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.pdfgen import canvas
from PIL import Image as PILImage
import qrcode


def create_certificate(user, course, enrollment=None, request=None):
    """
    Create a certificate for a user who completed a course.
    Automatically generates QR code and verification URL.
    
    Args:
        user: User instance
        course: Course instance
        enrollment: Enrollment instance (optional)
        request: HttpRequest instance (optional, for building absolute URLs)
    
    Returns:
        Certificate instance
    """
    from myApp.models import Certificate
    
    # Check if certificate already exists
    certificate, created = Certificate.objects.get_or_create(
        user=user,
        course=course,
        defaults={
            'title': f'Certificate of Completion - {course.title}',
            'enrollment': enrollment,
        }
    )
    
    # Generate QR code if not already generated
    if not certificate.qr_code or not certificate.verification_url:
        if request:
            base_url = request.build_absolute_uri('/')[:-1]  # Remove trailing slash
        else:
            base_url = getattr(settings, 'SITE_URL', 'https://fluentory.com')
        
        certificate.generate_qr_code(base_url=base_url)
    
    return certificate


def generate_certificate_pdf(certificate, request=None):
    """
    Generate a PDF certificate with QR code embedded.
    
    Args:
        certificate: Certificate instance
        request: HttpRequest instance (optional, for building absolute URLs)
    
    Returns:
        BytesIO buffer containing PDF
    """
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=36,
        textColor=colors.HexColor('#00655F'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Subtitle style
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=18,
        textColor=colors.HexColor('#666666'),
        spaceAfter=40,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    # Name style
    name_style = ParagraphStyle(
        'CustomName',
        parent=styles['Heading2'],
        fontSize=28,
        textColor=colors.HexColor('#00655F'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Course style
    course_style = ParagraphStyle(
        'CustomCourse',
        parent=styles['Normal'],
        fontSize=20,
        textColor=colors.HexColor('#333333'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    # Add spacing
    elements.append(Spacer(1, 0.5 * inch))
    
    # Certificate Title
    elements.append(Paragraph("Fluentory", title_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Certificate of Completion
    elements.append(Paragraph("Certificate of Completion", subtitle_style))
    elements.append(Spacer(1, 0.3 * inch))
    
    # This is to certify that
    certify_text = Paragraph(
        "This is to certify that",
        ParagraphStyle(
            'CertifyText',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
    )
    elements.append(certify_text)
    elements.append(Spacer(1, 0.1 * inch))
    
    # Student Name
    student_name = certificate.user.get_full_name() or certificate.user.username
    elements.append(Paragraph(student_name, name_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Has successfully completed
    complete_text = Paragraph(
        "has successfully completed the course",
        ParagraphStyle(
            'CompleteText',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
    )
    elements.append(complete_text)
    elements.append(Spacer(1, 0.1 * inch))
    
    # Course Title
    elements.append(Paragraph(certificate.course.title, course_style))
    elements.append(Spacer(1, 0.4 * inch))
    
    # Certificate Details Table
    data = [
        ['Issued:', certificate.issued_at.strftime('%B %d, %Y')],
        ['Certificate ID:', str(certificate.certificate_id)],
    ]
    
    table = Table(data, colWidths=[2 * inch, 4 * inch])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#333333')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # QR Code
    if certificate.qr_code:
        try:
            # Open QR code image
            qr_image = PILImage.open(certificate.qr_code.path)
            
            # Resize QR code to fit (2x2 inches)
            qr_image.thumbnail((2 * 72, 2 * 72), PILImage.Resampling.LANCZOS)
            
            # Save to BytesIO
            qr_buffer = BytesIO()
            qr_image.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            
            # Add QR code to PDF
            qr_img = Image(qr_buffer, width=1.5 * inch, height=1.5 * inch)
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(qr_img)
            
            # Verification text
            if certificate.verification_url:
                verify_text = Paragraph(
                    f"<para alignment='center'><font size=10 color='#666666'>Scan QR code to verify: {certificate.verification_url}</font></para>",
                    styles['Normal']
                )
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(verify_text)
        except Exception as e:
            # If QR code can't be loaded, just add text
            print(f"Warning: Could not load QR code image: {e}")
            if certificate.verification_url:
                verify_text = Paragraph(
                    f"<para alignment='center'><font size=10 color='#666666'>Verify at: {certificate.verification_url}</font></para>",
                    styles['Normal']
                )
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(verify_text)
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF value
    buffer.seek(0)
    return buffer


def save_certificate_pdf(certificate, request=None):
    """
    Generate and save PDF certificate to the certificate instance.
    
    Args:
        certificate: Certificate instance
        request: HttpRequest instance (optional)
    
    Returns:
        Certificate instance with pdf_file saved
    """
    pdf_buffer = generate_certificate_pdf(certificate, request)
    
    # Save PDF to certificate
    filename = f'certificate_{certificate.certificate_id}.pdf'
    certificate.pdf_file.save(filename, File(pdf_buffer), save=True)
    
    return certificate

