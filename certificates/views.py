
# from django.shortcuts import render, redirect
# from django.core.mail import EmailMessage
# from django.http import HttpResponse
# from .models import EmailNameData, Certificate, Coordinate
# from .forms import UploadEmailFileForm, UploadCertificateForm
# import base64
# from django.conf import settings
# from django.db import transaction
# from concurrent.futures import ThreadPoolExecutor
# import fitz



# def get_session_id(request):
#     """Ensure a unique session ID exists for the user."""
#     if not request.session.session_key:
#         request.session.create()
#     return request.session.session_key


# def upload_email_file(request):
#     session_id = get_session_id(request)

#     if request.method == 'POST':
#         form = UploadEmailFileForm(request.POST, request.FILES)
#         if form.is_valid():
#             file = request.FILES['file']
#             decoded_file = None

#             try:
#                 # Handle CSV and Excel files (without pandas for lighter approach)
#                 if file.name.endswith(('.xls', '.xlsx', '.xlsm')):
#                     from openpyxl import load_workbook
#                     wb = load_workbook(file)
#                     sheet = wb.active
#                     decoded_file = [
#                         (row[0].value, row[1].value) for row in sheet.iter_rows(min_row=2)
#                         if row[0].value and row[1].value  # Ensure both name and email are present
#                     ]
#                 else:
#                     decoded_file = [
#                         (line.decode('utf-8').split(',')[0], line.decode('utf-8').split(',')[1])
#                         for line in file.readlines() if line.decode('utf-8').split(',')[0] and line.decode('utf-8').split(',')[1]
#                     ]

#                 # Pre-fetch existing emails for faster filtering
#                 existing_emails = set(
#                     EmailNameData.objects.filter(session_id=session_id).values_list('email', flat=True)
#                 )

#                 # Bulk insert email and name data
#                 rows = [
#                     EmailNameData(name=row[0], email=row[1], session_id=session_id)
#                     for row in decoded_file if row[1] not in existing_emails and row[0]
#                 ]
#                 if rows:
#                     with transaction.atomic():
#                         EmailNameData.objects.bulk_create(rows)
#             except Exception as e:
#                 print(f"Error processing file: {e}")
#                 return HttpResponse("An error occurred while processing the file.", status=500)

#             return redirect('upload_certificate')
#     else:
#         form = UploadEmailFileForm()

#     return render(request, 'upload_email_file.html', {'form': form})



# def upload_certificate(request):
#     session_id = get_session_id(request)

#     if request.method == 'POST':
#         form = UploadCertificateForm(request.POST, request.FILES)
#         if form.is_valid():
#             try:
#                 file = request.FILES['file']
#                 with transaction.atomic():
#                     Certificate.objects.create(file=file.read(), session_id=session_id)
#                 return redirect('set_coordinates')
#             except Exception as e:
#                 print(f"Error saving certificate: {e}")
#                 return HttpResponse("An error occurred while uploading the certificate.", status=500)
#     else:
#         form = UploadCertificateForm()

#     return render(request, 'upload_certificate.html', {'form': form})

# def set_coordinates(request):
#     session_id = get_session_id(request)
#     certificate_image_data = None
#     certificate_width, certificate_height = 1000, 1000  # Default dimensions

#     try:
#         # Fetch the latest certificate for the session
#         certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')

#         # Convert PDF to an image for display
#         pdf_data = bytes(certificate.file)
#         pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
#         page = pdf_document[0]
#         pix = page.get_pixmap()
#         image_data = pix.tobytes("png")
#         certificate_image_data = base64.b64encode(image_data).decode('utf-8')

#         certificate_width = pix.width
#         certificate_height = pix.height
#     except Certificate.DoesNotExist:
#         return HttpResponse("Certificate not found for this session.", status=404)
#     except Exception as e:
#         print(f"Error processing certificate: {e}")
#         return HttpResponse("An error occurred while processing the certificate.", status=500)

#     if request.method == 'POST':
#         try:
#             x = float(request.POST.get('x'))
#             y = float(request.POST.get('y'))
#             font_size = int(request.POST.get('fontSize'))
#             font_color = request.POST.get('fontColor')

#             # Ensure that a valid certificate object is passed to the Coordinate
#             with transaction.atomic():
#                 Coordinate.objects.create(
#                     x=x,
#                     y=y,
#                     font_size=font_size,
#                     font_color=font_color,
#                     certificate=certificate,  # Assign the certificate object here
#                     session_id=session_id
#                 )
#             return redirect('send_emails')
#         except Exception as e:
#             print(f"Error saving coordinates: {e}")
#             return HttpResponse("An error occurred while saving the coordinates.", status=500)

#     return render(request, 'set_coordinates.html', {
#         'certificate_image_data': certificate_image_data,
#         'certificate_width': certificate_width,
#         'certificate_height': certificate_height
#     })
    

# import logging
# from django.core.mail import EmailMessage
# from django.conf import settings

# logger = logging.getLogger(__name__)

# def send_email_batch(emails_data, certificate_binary, coordinate):
#     logger.info(f"🟢 Starting email batch process for {len(emails_data)} recipients.")

#     for recipient in emails_data:
#         try:
#             clean_email = recipient.email.strip().replace("\r", "").replace("\n", "")
#             logger.debug(f"✉️ Sending email to: '{clean_email}'")

#             if not clean_email:
#                 logger.warning(f"⚠️ Skipping empty email for {recipient.name}")
#                 continue

#             email = EmailMessage(
#                 subject="🎉 Your Personalized Certificate is Ready! 🎓",
#                 body=f"Hi {recipient.name},\n\nYour certificate is ready!",
#                 from_email=settings.EMAIL_HOST_USER,
#                 to=[clean_email],
#             )
#             email.attach('certificate.pdf', certificate_binary, 'application/pdf')

#             response = email.send(fail_silently=False)  # 🔴 fail_silently=False to capture errors
#             logger.info(f"✅ Email send response for {clean_email}: {response}")

#             if response == 0:
#                 logger.error(f"❌ Email not sent to {clean_email}")

#         except Exception as e:
#             logger.error(f"❌ Error sending email to {recipient.email}: {e}", exc_info=True)

#     logger.info("✅ Email batch process completed.")


# def send_emails(request):
#     session_id = get_session_id(request)
#     try:
#         logger.info(f"Started email sending for session {session_id}")

#         certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
#         coordinate = Coordinate.objects.filter(session_id=session_id).first()

#         if not coordinate:
#             logger.error(f"Coordinates not found for session {session_id}")
#             return HttpResponse("Coordinates not found for this session.", status=404)

#         recipients = EmailNameData.objects.filter(session_id=session_id)
#         logger.info(f"Found {recipients.count()} recipients for session {session_id}")

#         # 🚨 Without ThreadPoolExecutor, sync mode for debugging
#         send_email_batch(recipients, certificate.file, coordinate)

#         return redirect('success')

#     except Exception as e:
#         logger.error(f"Error during email sending for session {session_id}: {e}")
#         return HttpResponse("An error occurred while sending emails.", status=500)

# def add_name_to_certificate(certificate_binary, name, x, y, font_size, font_color, font_name="MonteCarlo"):
#     """Add a name to a certificate PDF at specified coordinates."""
#     try:
#         from reportlab.pdfgen import canvas
#         from reportlab.pdfbase import pdfmetrics
#         from reportlab.pdfbase.ttfonts import TTFont
#         from PyPDF2 import PdfReader, PdfWriter
#         import io
#         import os
#         from django.conf import settings

#         # Register font if not already registered
#         font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "MonteCarlo-Regular.ttf")
#         pdfmetrics.registerFont(TTFont(font_name, font_path if os.path.exists(font_path) else "Helvetica"))

#         reader = PdfReader(io.BytesIO(certificate_binary))
#         writer = PdfWriter()
#         first_page = reader.pages[0]
#         page_width = float(first_page.mediabox.width)
#         page_height = float(first_page.mediabox.height)
#         y_inverted = page_height - y

#         packet = io.BytesIO()
#         can = canvas.Canvas(packet, pagesize=(page_width, page_height))
#         can.setFont(font_name, font_size)
#         can.setFillColorRGB(*[c / 255 for c in font_color])
#         can.drawString(x, y_inverted, name)
#         can.save()
#         packet.seek(0)

#         overlay_pdf = PdfReader(packet)
#         for page in reader.pages:
#             page.merge_page(overlay_pdf.pages[0])
#             writer.add_page(page)

#         output = io.BytesIO()
#         writer.write(output)
#         return output.getvalue()
#     except Exception as e:
#         print(f"Error adding name to certificate: {e}")
#         raise


# def success_view(request):
#     session_id = get_session_id(request)
#     try:
#         EmailNameData.objects.filter(session_id=session_id).delete()
#         Coordinate.objects.filter(session_id=session_id).delete()
#         Certificate.objects.filter(session_id=session_id).delete()
#     except Exception as e:
#         print(f"Error during cleanup: {e}")
#     return render(request, 'success.html')



# import os
# import io
# import base64
# import logging
# import fitz
# from django.shortcuts import render, redirect
# from django.core.mail import EmailMessage
# from django.http import HttpResponse
# from django.conf import settings
# from django.db import transaction
# from .models import EmailNameData, Certificate, Coordinate
# from .forms import UploadEmailFileForm, UploadCertificateForm
# from PyPDF2 import PdfReader, PdfWriter
# from reportlab.pdfgen import canvas
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont

# logger = logging.getLogger(__name__)

# def get_session_id(request):
#     if not request.session.session_key:
#         request.session.create()
#     return request.session.session_key


# def upload_email_file(request):
#     session_id = get_session_id(request)

#     if request.method == 'POST':
#         form = UploadEmailFileForm(request.POST, request.FILES)
#         if form.is_valid():
#             file = request.FILES['file']
#             try:
#                 decoded_file = []
#                 if file.name.endswith(('.xls', '.xlsx', '.xlsm')):
#                     from openpyxl import load_workbook
#                     wb = load_workbook(file)
#                     sheet = wb.active
#                     decoded_file = [
#                         (row[0].value, row[1].value) for row in sheet.iter_rows(min_row=2)
#                         if row[0].value and row[1].value
#                     ]
#                 else:
#                     decoded_file = [
#                         tuple(line.decode('utf-8').strip().split(',')[:2])
#                         for line in file.readlines() if ',' in line.decode('utf-8')
#                     ]

#                 # ✅ Log session ID for debugging
#                 print(f"📥 Uploading emails for session: {session_id}")

#                 existing_emails = set(
#                     EmailNameData.objects.filter(session_id=session_id).values_list('email', flat=True)
#                 )
#                 rows = [
#                     EmailNameData(name=row[0], email=row[1], session_id=session_id)
#                     for row in decoded_file if row[1] not in existing_emails and row[0]
#                 ]

#                 if rows:
#                     with transaction.atomic():
#                         EmailNameData.objects.bulk_create(rows)
#                         print(f"✅ {len(rows)} emails saved for session {session_id}")

#             except Exception as e:
#                 logger.error(f"Error processing file: {e}")
#                 return HttpResponse("An error occurred while processing the file.", status=500)

#             return redirect('upload_certificate')  # ✅ Ensure correct flow

#     form = UploadEmailFileForm()
#     return render(request, 'upload_email_file.html', {'form': form})



# def upload_certificate(request):
#     session_id = get_session_id(request)

#     if request.method == 'POST':
#         form = UploadCertificateForm(request.POST, request.FILES)
#         if form.is_valid():
#             try:
#                 file = request.FILES['file']
#                 with transaction.atomic():
#                     # ❌ The issue might be here: It always creates a new certificate
#                     Certificate.objects.filter(session_id=session_id).delete()  # Remove old to prevent duplicate
#                     Certificate.objects.create(file=file.read(), session_id=session_id)
#                 return redirect('set_coordinates')  # ✅ Ensure it moves forward
#             except Exception as e:
#                 logger.error(f"Error saving certificate: {e}")
#                 return HttpResponse("An error occurred while uploading the certificate.", status=500)
#     else:
#         # ✅ If a certificate already exists, skip the upload page
#         if Certificate.objects.filter(session_id=session_id).exists():
#             return redirect('set_coordinates')

#     form = UploadCertificateForm()
#     return render(request, 'upload_certificate.html', {'form': form})


# def set_coordinates(request):
#     session_id = get_session_id(request)

#     try:
#         certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
#         pdf_document = fitz.open(stream=bytes(certificate.file), filetype="pdf")
#         page = pdf_document[0]
#         pix = page.get_pixmap()
#         image_data = base64.b64encode(pix.tobytes("png")).decode('utf-8')

#         if request.method == 'POST':
#             try:
#                 x, y = float(request.POST.get('x')), float(request.POST.get('y'))
#                 font_size = int(request.POST.get('fontSize'))
#                 font_color = request.POST.get('fontColor')  # Expected format: "#RRGGBB"

#                 with transaction.atomic():
#                     Coordinate.objects.create(
#                         x=x, y=y, font_size=font_size, font_color=font_color,
#                         certificate=certificate, session_id=session_id
#                     )
#                 return redirect('send_emails')

#             except Exception as e:
#                 logger.error(f"Error saving coordinates: {e}")
#                 return HttpResponse("An error occurred while saving the coordinates.", status=500)

#         return render(request, 'set_coordinates.html', {
#             'certificate_image_data': image_data,
#             'certificate_width': pix.width,
#             'certificate_height': pix.height
#         })
#     except Certificate.DoesNotExist:
#         return HttpResponse("Certificate not found for this session.", status=404)
#     except Exception as e:
#         logger.error(f"Error processing certificate: {e}")
#         return HttpResponse("An error occurred while processing the certificate.", status=500)
    
# from django.core.mail import EmailMessage
# from django.conf import settings
# from django.http import HttpResponse
# from certificates.models import Certificate, Coordinate, EmailNameData

# def send_email_batch(emails_data, certificate_binary, coordinate):
#     print(f"🟢 Starting email batch process for {len(emails_data)} recipients.")

#     for recipient in emails_data:
#         try:
#             clean_email = recipient.email.strip().replace("\r", "").replace("\n", "")
#             print(f"✉️ Sending email to: '{clean_email}'")

#             if not clean_email:
#                 print(f"⚠️ Skipping empty email for {recipient.name}")
#                 continue

#             email = EmailMessage(
#                 subject="🎉 Your Personalized Certificate is Ready! 🎓",
#                 body=f"Hi {recipient.name},\n\nYour certificate is ready!",
#                 from_email=settings.EMAIL_HOST_USER,
#                 to=[clean_email],
#             )
#             email.attach('certificate.pdf', certificate_binary, 'application/pdf')

#             response = email.send(fail_silently=False)  
#             print(f"✅ Email send response for {clean_email}: {response}")

#             if response == 0:
#                 print(f"❌ Email not sent to {clean_email}")

#         except Exception as e:
#             print(f"❌ Error sending email to {recipient.email}: {str(e)}")

#     print("✅ Email batch process completed.")
    
# def send_emails(request):
#     session_id = get_session_id(request)
#     print(f"📩 Started email sending for session {session_id}")

#     try:
#         certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
#         print(f"📜 Certificate found for session {session_id}")

#         coordinate = Coordinate.objects.filter(session_id=session_id).first()
#         if not coordinate:
#             print(f"❌ Coordinates not found for session {session_id}")
#             return HttpResponse("Coordinates not found for this session.", status=404)

#         recipients = EmailNameData.objects.filter(session_id=session_id)
#         print(f"📧 Found {recipients.count()} recipients for session {session_id}")

#         # 🔹 FIX: Check if recipients exist
#         if not recipients.exists():
#             print("⚠️ No recipients found for this session")
#             return HttpResponse("No recipients found.", status=404)

#         # ✅ FIX: Ensure the certificate binary is loaded correctly
#         certificate_binary = bytes(certificate.file)
#         print("📄 Certificate file loaded successfully.")

#         send_email_batch(recipients, certificate_binary, coordinate)
#         print("✅ Emails sent successfully!")
#         return HttpResponse("Emails sent successfully!", status=200)

#     except Exception as e:
#         print(f"❌ Error in send_emails: {str(e)}")
#         return HttpResponse("Internal server error.", status=500)



# def add_name_to_certificate(certificate_binary, name, x, y, font_size, font_color):
#     try:
#         font_name = "MonteCarlo"
#         font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "MonteCarlo-Regular.ttf")
#         if not os.path.exists(font_path):
#             font_name = "Helvetica"

#         pdfmetrics.registerFont(TTFont(font_name, font_path if os.path.exists(font_path) else "Helvetica"))

#         reader = PdfReader(io.BytesIO(certificate_binary))
#         writer = PdfWriter()
#         first_page = reader.pages[0]
#         page_width = float(first_page.mediabox.width)
#         page_height = float(first_page.mediabox.height)
#         y_inverted = page_height - y  # Flip Y coordinate

#         packet = io.BytesIO()
#         can = canvas.Canvas(packet, pagesize=(page_width, page_height))
#         can.setFont(font_name, font_size)

#         r, g, b = [int(font_color[i:i+2], 16) / 255 for i in (1, 3, 5)]  # Convert "#RRGGBB" to RGB
#         can.setFillColorRGB(r, g, b)

#         can.drawString(x, y_inverted, name)
#         can.save()
#         packet.seek(0)

#         overlay_pdf = PdfReader(packet)
#         for page in reader.pages:
#             page.merge_page(overlay_pdf.pages[0])
#             writer.add_page(page)

#         output = io.BytesIO()
#         writer.write(output)
#         return output.getvalue()
#     except Exception as e:
#         logger.error(f"Error adding name to certificate: {e}")
#         raise



# import os
# import io
# import base64
# import logging
# import fitz
# from django.shortcuts import render, redirect
# from django.core.mail import EmailMessage
# from django.http import HttpResponse
# from django.conf import settings
# from django.db import transaction
# from .models import EmailNameData, Certificate, Coordinate
# from .forms import UploadEmailFileForm, UploadCertificateForm
# from PyPDF2 import PdfReader, PdfWriter
# from reportlab.pdfgen import canvas
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont
# import pandas as pd
# from io import StringIO
# import csv

# def get_session_id(request):
#     """Ensure a unique session ID exists for the user."""
#     if not request.session.session_key:
#         request.session.create()
#     return request.session.session_key


# def upload_email_file(request):
#     session_id = get_session_id(request)

#     if request.method == 'POST':
#         form = UploadEmailFileForm(request.POST, request.FILES)
#         if form.is_valid():
#             file = request.FILES['file']
#             decoded_file = None

#             # Check file extension and process
#             if file.name.endswith(('.xls', '.xlsx', '.xlsm')):
#                 excel_data = pd.read_excel(file)
#                 csv_data = StringIO()
#                 excel_data.to_csv(csv_data, index=False)
#                 csv_data.seek(0)
#                 decoded_file = csv_data.getvalue().splitlines()
#             else:
#                 decoded_file = file.read().decode('utf-8').splitlines()

#             # Bulk insert email and name data
#             rows = []
#             reader = csv.reader(decoded_file)
#             for row in reader:
#                 name, email = row
#                 if not EmailNameData.objects.filter(email=email, session_id=session_id).exists():
#                     rows.append(EmailNameData(name=name, email=email, session_id=session_id))
            
#             # Use bulk_create to optimize database insertion
#             if rows:
#                 EmailNameData.objects.bulk_create(rows)

#             return redirect('upload_certificate')
#     else:
#         form = UploadEmailFileForm()

#     return render(request, 'upload_email_file.html', {'form': form})

# logger = logging.getLogger(__name__)

# # def get_session_id(request):
# #     if not request.session.session_key:
# #         request.session.create()
# #     return request.session.session_key

# # 📥 Email Upload

# # def upload_email_file(request):
# #     session_id = get_session_id(request)

# #     if request.method == 'POST':
# #         form = UploadEmailFileForm(request.POST, request.FILES)
# #         if form.is_valid():
# #             file = request.FILES['file']
# #             decoded_file = None

# #             try:
# #                 # Handle CSV and Excel files (without pandas for lighter approach)
# #                 if file.name.endswith(('.xls', '.xlsx', '.xlsm')):
# #                     from openpyxl import load_workbook
# #                     wb = load_workbook(file)
# #                     sheet = wb.active
# #                     decoded_file = [
# #                         (row[0].value, row[1].value) for row in sheet.iter_rows(min_row=2)
# #                         if row[0].value and row[1].value  # Ensure both name and email are present
# #                     ]
# #                 else:
# #                     decoded_file = [
# #                         (line.decode('utf-8').split(',')[0], line.decode('utf-8').split(',')[1])
# #                         for line in file.readlines() if line.decode('utf-8').split(',')[0] and line.decode('utf-8').split(',')[1]
# #                     ]

# #                 # Pre-fetch existing emails for faster filtering
# #                 existing_emails = set(
# #                     EmailNameData.objects.filter(session_id=session_id).values_list('email', flat=True)
# #                 )

# #                 # Bulk insert email and name data
# #                 rows = [
# #                     EmailNameData(name=row[0], email=row[1], session_id=session_id)
# #                     for row in decoded_file if row[1] not in existing_emails and row[0]
# #                 ]
# #                 if rows:
# #                     with transaction.atomic():
# #                         EmailNameData.objects.bulk_create(rows)
# #             except Exception as e:
# #                 print(f"Error processing file: {e}")
# #                 return HttpResponse("An error occurred while processing the file.", status=500)

# #             return redirect('upload_certificate')
# #     else:
# #         form = UploadEmailFileForm()

# #     return render(request, 'upload_email_file.html', {'form': form})
# # from openpyxl import load_workbook
# # def upload_email_file(request):
# #     session_id = get_session_id(request)

# #     if request.method == 'POST':
# #         form = UploadEmailFileForm(request.POST, request.FILES)
# #         if form.is_valid():
# #             file = request.FILES['file']
# #             decoded_file = []

# #             try:
# #                 # ✅ Handle CSV and Excel files properly
# #                 if file.name.endswith(('.xls', '.xlsx', '.xlsm')):
# #                     wb = load_workbook(file)
# #                     sheet = wb.active
# #                     decoded_file = [
# #                         (row[0].value.strip(), row[1].value.strip()) for row in sheet.iter_rows(min_row=2)
# #                         if row[0].value and row[1].value  # Ensure both name and email are present
# #                     ]
# #                 else:
# #                     decoded_file = [
# #                         (line.decode('utf-8').strip().split(',')[0], line.decode('utf-8').strip().split(',')[1])
# #                         for line in file.readlines() if len(line.decode('utf-8').strip().split(',')) >= 2
# #                     ]

# #                 # ✅ Optimize database query by prefetching emails
# #                 existing_emails = set(
# #                     EmailNameData.objects.filter(session_id=session_id).values_list('email', flat=True)
# #                 )

# #                 # ✅ Bulk insert filtered data
# #                 rows = [
# #                     EmailNameData(name=row[0], email=row[1], session_id=session_id)
# #                     for row in decoded_file if row[1] not in existing_emails and row[0]
# #                 ]
# #                 if rows:
# #                     with transaction.atomic():
# #                         EmailNameData.objects.bulk_create(rows)

# #             except Exception as e:
# #                 print(f"Error processing file: {e}")
# #                 return HttpResponse("An error occurred while processing the file.", status=500)

# #             return redirect('upload_certificate')

# #     else:
# #         form = UploadEmailFileForm()

# #     return render(request, 'upload_email_file.html', {'form': form})


# def upload_certificate(request):
#     session_id = get_session_id(request)

#     if request.method == 'POST':
#         form = UploadCertificateForm(request.POST, request.FILES)
#         if form.is_valid():
#             file = request.FILES['file']
#             # Save the certificate in the database
#             Certificate.objects.create(file=file.read(), session_id=session_id)
#             return redirect('set_coordinates')
#     else:
#         form = UploadCertificateForm()

#     return render(request, 'upload_certificate.html', {'form': form})



# # def upload_certificate(request):
# #     session_id = get_session_id(request)

# #     if request.method == 'POST':
# #         form = UploadCertificateForm(request.POST, request.FILES)
# #         if form.is_valid():
# #             try:
# #                 file = request.FILES['file']
# #                 with transaction.atomic():
# #                     # ❌ The issue might be here: It always creates a new certificate
# #                     Certificate.objects.filter(session_id=session_id).delete()  # Remove old to prevent duplicate
# #                     Certificate.objects.create(file=file.read(), session_id=session_id)
# #                 return redirect('set_coordinates')  # ✅ Ensure it moves forward
# #             except Exception as e:
# #                 logger.error(f"Error saving certificate: {e}")
# #                 return HttpResponse("An error occurred while uploading the certificate.", status=500)
# #     else:
# #         # ✅ If a certificate already exists, skip the upload page
# #         if Certificate.objects.filter(session_id=session_id).exists():
# #             return redirect('set_coordinates')

# #     form = UploadCertificateForm()
# #     return render(request, 'upload_certificate.html', {'form': form})



# # 📍 Setting Coordinates

# def set_coordinates(request):
#     session_id = get_session_id(request)

#     try:
#         certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
#         pdf_document = fitz.open(stream=bytes(certificate.file), filetype="pdf")
#         page = pdf_document[0]
#         pix = page.get_pixmap()
#         image_data = base64.b64encode(pix.tobytes("png")).decode('utf-8')

#         if request.method == 'POST':
#             try:
#                 x, y = float(request.POST.get('x')), float(request.POST.get('y'))
#                 font_size = int(request.POST.get('fontSize'))
#                 font_color = request.POST.get('fontColor')

#                 with transaction.atomic():
#                     Coordinate.objects.create(
#                         x=x, y=y, font_size=font_size, font_color=font_color,
#                         certificate=certificate, session_id=session_id
#                     )
#                 return redirect('send_emails')

#             except Exception as e:
#                 logger.error(f"Error saving coordinates: {e}")
#                 return HttpResponse("Error saving coordinates.", status=500)

#         return render(request, 'set_coordinates.html', {
#             'certificate_image_data': image_data,
#             'certificate_width': pix.width,
#             'certificate_height': pix.height
#         })
#     except Certificate.DoesNotExist:
#         return HttpResponse("Certificate not found.", status=404)
#     except Exception as e:
#         logger.error(f"Error processing certificate: {e}")
#         return HttpResponse("Error processing certificate.", status=500)

# # ✉️ Email Sending
# def send_email_batch(emails_data, certificate_binary, coordinate):
#     print(f"🟢 Starting email batch process for {len(emails_data)} recipients.")

#     for recipient in emails_data:
#         try:
#             clean_email = recipient.email.strip().replace("\r", "").replace("\n", "")
#             if not clean_email:
#                 print(f"⚠️ Skipping empty email for {recipient.name}")
#                 continue

#             print(f"🔹 Adding name to certificate: {recipient.name} at ({coordinate.x}, {coordinate.y})")

#             # ✅ Fix: Generate personalized certificate with name
#             modified_certificate = add_name_to_certificate(
#                 certificate_binary, recipient.name, coordinate.x, coordinate.y, coordinate.font_size, coordinate.font_color
#             )

#             print(f"📜 Certificate binary size after modification: {len(modified_certificate)} bytes")

#             email = EmailMessage(
#                 subject="🎉 Your Personalized Certificate is Ready! 🎓",
#                 body=f"Hi {recipient.name},\n\nYour certificate is ready!",
#                 from_email=settings.EMAIL_HOST_USER,
#                 to=[clean_email],
#             )
#             email.attach('certificate.pdf', modified_certificate, 'application/pdf')

#             response = email.send(fail_silently=False)  
#             print(f"✅ Email send response for {clean_email}: {response}")

#             if response == 0:
#                 print(f"❌ Email not sent to {clean_email}")

#         except Exception as e:
#             print(f"❌ Error sending email to {recipient.email}: {str(e)}")

#     print("✅ Email batch process completed.")


# def send_emails(request):
#     print("🚀 send_emails function executed!")  
#     session_id = get_session_id(request)

#     try:
#         certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
#         coordinate = Coordinate.objects.filter(session_id=session_id).first()
#         recipients = EmailNameData.objects.filter(session_id=session_id)

#         if not coordinate or not recipients.exists():
#             return HttpResponse("Missing coordinates or recipients.", status=404)

#         certificate_binary = bytes(certificate.file)
#         send_email_batch(recipients, certificate_binary, coordinate)

#         # return HttpResponse("Emails sent successfully!", status=200)
#         return redirect('success')

#     except Exception as e:
#         logger.error(f"Error in send_emails: {str(e)}")
#         return HttpResponse("Internal server error.", status=500)

# # ✏️ Add Name to Certificate

# def add_name_to_certificate(certificate_binary, name, x, y, font_size, font_color):
#     try:
#         font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "MonteCarlo-Regular.ttf")
#         font_name = "Helvetica" if not os.path.exists(font_path) else "MonteCarlo"

#         pdfmetrics.registerFont(TTFont(font_name, font_path if os.path.exists(font_path) else "Helvetica"))

#         reader = PdfReader(io.BytesIO(certificate_binary))
#         writer = PdfWriter()
#         first_page = reader.pages[0]
#         page_width = float(first_page.mediabox.width)
#         page_height = float(first_page.mediabox.height)

#         print(f"🔹 PDF Size: {page_width} x {page_height}")
#         print(f"🖋️ Adding Name: '{name}' at ({x}, {y}) with font {font_name} ({font_size}px)")

#         # Convert font_color "#RRGGBB" to RGB
#         r, g, b = [int(font_color[i:i+2], 16) / 255 for i in (1, 3, 5)]

#         # Create new PDF with name overlay
#         packet = io.BytesIO()
#         can = canvas.Canvas(packet, pagesize=(page_width, page_height))
#         can.setFont(font_name, font_size)
#         can.setFillColorRGB(r, g, b)

#         # 🔹 Fix Y-Coordinate (invert it for PDF positioning)
#         y_inverted = page_height - y
#         can.drawString(x, y_inverted, name)
#         can.save()

#         # Merge the overlay
#         packet.seek(0)
#         overlay_pdf = PdfReader(packet)
#         first_page.merge_page(overlay_pdf.pages[0])
#         writer.add_page(first_page)

#         output = io.BytesIO()
#         writer.write(output)
#         return output.getvalue()

#     except Exception as e:
#         logger.error(f"❌ Error adding name to certificate: {e}")
#         raise




# def success_view(request):
#     session_id = get_session_id(request)
#     EmailNameData.objects.filter(session_id=session_id).delete()
#     Coordinate.objects.filter(session_id=session_id).delete()
#     Certificate.objects.filter(session_id=session_id).delete()
#     return render(request, 'success.html')




# import os
# import io
# import base64
# import logging
# import fitz
# import pandas as pd
# import csv
# from io import StringIO
# from django.shortcuts import render, redirect
# from django.core.mail import EmailMessage
# from django.http import HttpResponse
# from django.conf import settings
# from django.db import transaction
# from PyPDF2 import PdfReader, PdfWriter
# from reportlab.pdfgen import canvas
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont
# from .models import EmailNameData, Certificate, Coordinate
# from .forms import UploadEmailFileForm, UploadCertificateForm

# # Configure Logger
# logger = logging.getLogger(__name__)

# def get_session_id(request):
#     """Ensure a unique session ID exists for the user."""
#     if not request.session.session_key:
#         request.session.create()
#     return request.session.session_key

# # 📩 Upload Email File
# def upload_email_file(request):
#     session_id = get_session_id(request)

#     if request.method == 'POST':
#         form = UploadEmailFileForm(request.POST, request.FILES)
#         if form.is_valid():
#             file = request.FILES['file']
#             decoded_file = None

#             # Convert Excel to CSV format
#             if file.name.endswith(('.xls', '.xlsx', '.xlsm')):
#                 csv_data = StringIO()
#                 pd.read_excel(file).to_csv(csv_data, index=False)
#                 csv_data.seek(0)
#                 decoded_file = csv_data.getvalue().splitlines()
#             else:
#                 decoded_file = file.read().decode('utf-8').splitlines()

#             # Bulk insert email and name data
#             rows = []
#             for row in csv.reader(decoded_file):
#                 name, email = row
#                 if not EmailNameData.objects.filter(email=email, session_id=session_id).exists():
#                     rows.append(EmailNameData(name=name, email=email, session_id=session_id))

#             if rows:
#                 EmailNameData.objects.bulk_create(rows)

#             return redirect('upload_certificate')
#     else:
#         form = UploadEmailFileForm()

#     return render(request, 'upload_email_file.html', {'form': form})

# # 📜 Upload Certificate
# def upload_certificate(request):
#     session_id = get_session_id(request)

#     if request.method == 'POST':
#         form = UploadCertificateForm(request.POST, request.FILES)
#         if form.is_valid():
#             file = request.FILES['file']
#             Certificate.objects.create(file=file.read(), session_id=session_id)  # Save as Binary
#             return redirect('set_coordinates')
#     else:
#         form = UploadCertificateForm()

#     return render(request, 'upload_certificate.html', {'form': form})

# # 📍 Set Coordinates
# def set_coordinates(request):
#     session_id = get_session_id(request)

#     try:
#         certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
#         pdf_document = fitz.open(stream=bytes(certificate.file), filetype="pdf")
#         page = pdf_document[0]
#         pix = page.get_pixmap()
#         image_data = base64.b64encode(pix.tobytes("png")).decode('utf-8')

#         if request.method == 'POST':
#             try:
#                 x, y = float(request.POST.get('x')), float(request.POST.get('y'))
#                 font_size = int(request.POST.get('fontSize'))
#                 font_color = request.POST.get('fontColor')

#                 with transaction.atomic():
#                     Coordinate.objects.create(
#                         x=x, y=y, font_size=font_size, font_color=font_color,
#                         certificate=certificate, session_id=session_id
#                     )
#                 return redirect('send_emails')

#             except Exception as e:
#                 logger.error(f"Error saving coordinates: {e}")
#                 return HttpResponse("Error saving coordinates.", status=500)

#         return render(request, 'set_coordinates.html', {
#             'certificate_image_data': image_data,
#             'certificate_width': pix.width,
#             'certificate_height': pix.height
#         })
#     except Certificate.DoesNotExist:
#         return HttpResponse("Certificate not found.", status=404)
#     except Exception as e:
#         logger.error(f"Error processing certificate: {e}")
#         return HttpResponse("Error processing certificate.", status=500)

# # ✉️ Send Emails
# def send_email_batch(recipients, certificate_binary, coordinate):
#     """Send a batch of emails with personalized certificates."""
#     logger.info(f"Starting email batch for {len(recipients)} recipients.")

#     for recipient in recipients:
#         try:
#             clean_email = recipient.email.strip()
#             if not clean_email:
#                 logger.warning(f"Skipping empty email for {recipient.name}")
#                 continue

#             logger.info(f"Adding name to certificate: {recipient.name} at ({coordinate.x}, {coordinate.y})")

#             # Generate personalized certificate
#             modified_certificate = add_name_to_certificate(
#                 certificate_binary, recipient.name, coordinate.x, coordinate.y, coordinate.font_size, coordinate.font_color
#             )

#             email = EmailMessage(
#                 subject="Your Personalized Certificate is Ready!",
#                 body=f"Hi {recipient.name},\n\nYour certificate is ready!",
#                 from_email=settings.EMAIL_HOST_USER,
#                 to=[clean_email],
#             )
#             email.attach('certificate.pdf', modified_certificate, 'application/pdf')

#             response = email.send(fail_silently=False)
#             if response == 0:
#                 logger.error(f"Email not sent to {clean_email}")

#         except Exception as e:
#             logger.error(f"Error sending email to {recipient.email}: {str(e)}")

#     logger.info("Email batch process completed.")

# def send_emails(request):
#     """Fetch emails, generate certificates, and send emails."""
#     session_id = get_session_id(request)

#     try:
#         certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
#         coordinate = Coordinate.objects.filter(session_id=session_id).first()
#         recipients = EmailNameData.objects.filter(session_id=session_id)

#         if not coordinate or not recipients.exists():
#             return HttpResponse("Missing coordinates or recipients.", status=404)

#         certificate_binary = bytes(certificate.file)
#         send_email_batch(recipients, certificate_binary, coordinate)

#         return redirect('success')

#     except Exception as e:
#         logger.error(f"Error in send_emails: {str(e)}")
#         return HttpResponse("Internal server error.", status=500)

# # ✏️ Add Name to Certificate
# def add_name_to_certificate(certificate_binary, name, x, y, font_size, font_color):
#     """Overlay name on a certificate and return the modified PDF."""
#     try:
#         font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "MonteCarlo-Regular.ttf")
#         font_name = "Helvetica" if not os.path.exists(font_path) else "MonteCarlo"

#         pdfmetrics.registerFont(TTFont(font_name, font_path if os.path.exists(font_path) else "Helvetica"))

#         reader = PdfReader(io.BytesIO(certificate_binary))
#         writer = PdfWriter()
#         first_page = reader.pages[0]
#         page_width = float(first_page.mediabox.width)
#         page_height = float(first_page.mediabox.height)

#         r, g, b = [int(font_color[i:i+2], 16) / 255 for i in (1, 3, 5)]

#         # Create new PDF with name overlay
#         packet = io.BytesIO()
#         can = canvas.Canvas(packet, pagesize=(page_width, page_height))
#         can.setFont(font_name, font_size)
#         can.setFillColorRGB(r, g, b)

#         y_inverted = page_height - y
#         can.drawString(x, y_inverted, name)
#         can.save()

#         # Merge the overlay
#         packet.seek(0)
#         overlay_pdf = PdfReader(packet)
#         first_page.merge_page(overlay_pdf.pages[0])
#         writer.add_page(first_page)

#         output = io.BytesIO()
#         writer.write(output)
#         return output.getvalue()

#     except Exception as e:
#         logger.error(f"Error adding name to certificate: {e}")
#         raise

# # ✅ Success View
# def success_view(request):
#     session_id = get_session_id(request)
#     EmailNameData.objects.filter(session_id=session_id).delete()
#     Coordinate.objects.filter(session_id=session_id).delete()
#     Certificate.objects.filter(session_id=session_id).delete()
#     return render(request, 'success.html')

import os
import io
import base64
import logging
import fitz
import pandas as pd
import csv
from io import StringIO
from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.conf import settings
from django.db import transaction
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .models import EmailNameData, Certificate, Coordinate
from .forms import UploadEmailFileForm, UploadCertificateForm

# Configure Logger
logger = logging.getLogger(__name__)

def get_session_id(request):
    """Ensure a unique session ID exists for the user."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

# 📩 Upload Email File
def upload_email_file(request):
    session_id = get_session_id(request)

    if request.method == 'POST':
        form = UploadEmailFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            decoded_file = None

            if file.name.endswith(('.xls', '.xlsx', '.xlsm')):
                csv_data = StringIO()
                pd.read_excel(file).to_csv(csv_data, index=False)
                csv_data.seek(0)
                decoded_file = csv_data.getvalue().splitlines()
            else:
                decoded_file = file.read().decode('utf-8').splitlines()

            rows = [
                EmailNameData(name=row[0], email=row[1], session_id=session_id)
                for row in csv.reader(decoded_file)
                if not EmailNameData.objects.filter(email=row[1], session_id=session_id).exists()
            ]

            if rows:
                EmailNameData.objects.bulk_create(rows)

            return redirect('upload_certificate')  # 🔄 Redirect to Upload Certificate

    else:
        form = UploadEmailFileForm()

    return render(request, 'upload_email_file.html', {'form': form})

# 📜 Upload Certificate
def upload_certificate(request):
    session_id = get_session_id(request)

    if request.method == 'POST':
        form = UploadCertificateForm(request.POST, request.FILES)
        if form.is_valid():
            Certificate.objects.create(file=request.FILES['file'].read(), session_id=session_id)
            return redirect('set_coordinates')  # 🔄 Redirect to Set Coordinates

    else:
        form = UploadCertificateForm()

    return render(request, 'upload_certificate.html', {'form': form})

# 📍 Set Coordinates
def set_coordinates(request):
    session_id = get_session_id(request)

    try:
        certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
        pdf_document = fitz.open(stream=bytes(certificate.file), filetype="pdf")
        page = pdf_document[0]
        pix = page.get_pixmap()
        image_data = base64.b64encode(pix.tobytes("png")).decode('utf-8')

        if request.method == 'POST':
            x, y = float(request.POST.get('x')), float(request.POST.get('y')) - 9
            font_size = int(request.POST.get('fontSize'))
            font_color = request.POST.get('fontColor')

            with transaction.atomic():
                Coordinate.objects.create(
                    x=x, y=y, font_size=font_size, font_color=font_color,
                    certificate=certificate, session_id=session_id
                )

            return redirect('send_emails')  # 🔄 Redirect to Send Emails

        return render(request, 'set_coordinates.html', {
            'certificate_image_data': image_data,
            'certificate_width': pix.width,
            'certificate_height': pix.height
        })

    except Certificate.DoesNotExist:
        return HttpResponse("Certificate not found.", status=404)
    except Exception as e:
        logger.error(f"Error processing certificate: {e}")
        return HttpResponse("Error processing certificate.", status=500)

# ✉️ Send Emails
def send_email_batch(recipients, certificate_binary, coordinate):
    """Send a batch of emails with personalized certificates."""
    logger.info(f"Starting email batch for {len(recipients)} recipients.")

    for recipient in recipients:
        try:
            clean_email = recipient.email.strip()
            if not clean_email:
                logger.warning(f"Skipping empty email for {recipient.name}")
                continue
            print(f"Adding name to certificate: {recipient.name} at ({coordinate.x}, {coordinate.y})")
            logger.info(f"Adding name to certificate: {recipient.name} at ({coordinate.x}, {coordinate.y})")

            # Generate personalized certificate
            modified_certificate = add_name_to_certificate(
                certificate_binary, recipient.name, coordinate.x, coordinate.y, coordinate.font_size, coordinate.font_color
            )

            email = EmailMessage(
                subject="Your Personalized Certificate is Ready!",
                body=f"Hi {recipient.name},\n\nYour certificate is ready!",
                from_email=settings.EMAIL_HOST_USER,
                to=[clean_email],
            )
            email.attach('certificate.pdf', modified_certificate, 'application/pdf')

            response = email.send(fail_silently=False)
            if response == 0:
                logger.error(f"Email not sent to {clean_email}")

        except Exception as e:
            logger.error(f"Error sending email to {recipient.email}: {str(e)}")

    logger.info("Email batch process completed.")

def send_emails(request):
    """Fetch emails, generate certificates, and send emails."""
    session_id = get_session_id(request)

    try:
        certificate = Certificate.objects.filter(session_id=session_id).latest('uploaded_at')
        coordinate = Coordinate.objects.filter(session_id=session_id).first()
        recipients = EmailNameData.objects.filter(session_id=session_id)

        if not coordinate or not recipients.exists():
            return HttpResponse("Missing coordinates or recipients.", status=404)

        certificate_binary = bytes(certificate.file)
        send_email_batch(recipients, certificate_binary, coordinate)

        return redirect('success')  # 🔄 Redirect to Success Page

    except Exception as e:
        logger.error(f"Error in send_emails: {str(e)}")
        return HttpResponse("Internal server error.", status=500)

# ✏️ Add Name to Certificate
def add_name_to_certificate(certificate_binary, name, x, y, font_size, font_color):
    """Overlay name on a certificate and return the modified PDF."""
    try:
        font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "MonteCarlo-Regular.ttf")
        font_name = "Helvetica" if not os.path.exists(font_path) else "MonteCarlo"

        pdfmetrics.registerFont(TTFont(font_name, font_path if os.path.exists(font_path) else "Helvetica"))

        reader = PdfReader(io.BytesIO(certificate_binary))
        writer = PdfWriter()
        first_page = reader.pages[0]
        page_width = float(first_page.mediabox.width)
        page_height = float(first_page.mediabox.height)

        r, g, b = [int(font_color[i:i+2], 16) / 255 for i in (1, 3, 5)]

        # Create new PDF with name overlay
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))
        can.setFont(font_name, font_size)
        can.setFillColorRGB(r, g, b)

        y_inverted = page_height - y
        can.drawString(x, y_inverted, name)
        can.save()

        # Merge the overlay
        packet.seek(0)
        overlay_pdf = PdfReader(packet)
        first_page.merge_page(overlay_pdf.pages[0])
        writer.add_page(first_page)

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()

    except Exception as e:
        logger.error(f"Error adding name to certificate: {e}")
        raise

# ✅ Success View
def success_view(request):
    session_id = get_session_id(request)
    EmailNameData.objects.filter(session_id=session_id).delete()
    Coordinate.objects.filter(session_id=session_id).delete()
    Certificate.objects.filter(session_id=session_id).delete()
    return render(request, 'success.html')
