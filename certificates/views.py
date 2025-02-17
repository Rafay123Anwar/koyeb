import os
import io
import csv
import base64
from django.conf import settings
from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
from .models import EmailNameData, Certificate, Coordinate
from .forms import UploadEmailFileForm, UploadCertificateForm


# Ensure a unique session ID for the user
def get_session_id(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


# Upload Email File
def upload_email_file(request):
    session_id = get_session_id(request)

    if request.method == 'POST':
        form = UploadEmailFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            decoded_file = file.read().decode('utf-8').splitlines()
            reader = csv.reader(decoded_file)
            for row in reader:
                name, email = row
                EmailNameData.objects.create(name=name, email=email, session_id=session_id)
            return redirect('upload_certificate')
    else:
        form = UploadEmailFileForm()

    return render(request, 'upload_email_file.html', {'form': form})


# Upload Certificate File
def upload_certificate(request):
    session_id = get_session_id(request)

    if request.method == 'POST':
        form = UploadCertificateForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            Certificate.objects.create(file=file.read(), session_id=session_id)
            return redirect('set_coordinates')
    else:
        form = UploadCertificateForm()

    return render(request, 'upload_certificate.html', {'form': form})


# Convert Hex Color to RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError("Invalid hex color format. Use a 6-character hex code like '#ffbb00'.")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


# Set Coordinates for the Certificate
def set_coordinates(request):
    session_id = get_session_id(request)
    certificate_image_data = None

    try:
        certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')

        if certificate.file:
            pdf_data = bytes(certificate.file)
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            page = pdf_document[0]
            pix = page.get_pixmap()
            image_data = pix.tobytes("png")
            certificate_image_data = base64.b64encode(image_data).decode('utf-8')

    except Certificate.DoesNotExist:
        return redirect('error_page')
    except Exception as e:
        print(f"Error processing certificate: {e}")
        return redirect('error_page')

    if request.method == 'POST':
        try:
            x = float(request.POST.get('x'))
            y = float(request.POST.get('y'))
            font_size = int(request.POST.get('fontSize'))
            font_color = request.POST.get('fontColor')

            Coordinate.objects.create(
                x=x, y=y,
                font_size=font_size,
                font_color=font_color,
                certificate=certificate,
                session_id=session_id
            )
            return redirect('send_emails')
        except Exception as e:
            print(f"Error saving coordinates: {e}")

    return render(request, 'set_coordinates.html', {
        'certificate_image_data': certificate_image_data,
    })


# Add Name to Certificate
def add_name_to_certificate(certificate_binary, name, x, y, font_size, font_color, font_name="MonteCarlo"):
    try:
        # font_path = os.path.join(settings.BASE_DIR, "MonteCarlo-Regular.ttf")
        font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "MonteCarlo-Regular.ttf")

        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        else:
            print("Font not found, using default.")
            font_name = "Helvetica"

        reader = PdfReader(io.BytesIO(certificate_binary))
        writer = PdfWriter()
        first_page = reader.pages[0]
        y_inverted = float(first_page.mediabox.height) - y

        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(float(first_page.mediabox.width), float(first_page.mediabox.height)))
        can.setFont(font_name, font_size)
        can.setFillColorRGB(*(c / 255 for c in font_color))
        can.drawString(x, y_inverted, name)
        can.save()
        packet.seek(0)

        overlay_pdf = PdfReader(packet)
        for page in reader.pages:
            page.merge_page(overlay_pdf.pages[0])
            writer.add_page(page)

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()

    except Exception as e:
        print(f"Error adding name to certificate: {e}")
        raise


# Send Emails with Certificates
def send_emails(request):
    session_id = get_session_id(request)

    try:
        certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
        coordinate = certificate.coordinates.filter(session_id=session_id).first()
        recipients = EmailNameData.objects.filter(session_id=session_id)

        for recipient in recipients:
            font_color_rgb = hex_to_rgb(coordinate.font_color)
            modified_pdf_data = add_name_to_certificate(
                certificate_binary=certificate.file,
                name=recipient.name,
                x=coordinate.x,
                y=coordinate.y,
                font_size=coordinate.font_size,
                font_color=font_color_rgb
            )

            email = EmailMessage(
                subject="🎉 Your Personalized Certificate!",
                body=f"Hi {recipient.name},\nYour certificate is attached.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient.email]
            )
            email.attach('certificate.pdf', modified_pdf_data, 'application/pdf')
            email.send()

        return redirect('success')

    except Exception as e:
        print(f"Error sending emails: {e}")
        return redirect('error_page')


# Success View
def success_view(request):
    session_id = get_session_id(request)

    try:
        EmailNameData.objects.filter(session_id=session_id).delete()
        Coordinate.objects.filter(session_id=session_id).delete()
        Certificate.objects.filter(session_id=session_id).delete()
    except Exception as e:
        print(f"Error clearing session data: {e}")

    return render(request, 'success.html')
