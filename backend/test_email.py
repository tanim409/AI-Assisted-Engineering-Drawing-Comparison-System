import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "tanimasif409@gmail.com"
SMTP_PASSWORD = "lmbicoznuurpyevt"
SMTP_FROM = "tanimasif409@gmail.com"
to_email = "tanimasif409@gmail.com"

msg = MIMEMultipart("alternative")
msg["Subject"] = "Test email"
msg["From"] = SMTP_FROM
msg["To"] = to_email

msg.attach(MIMEText("Test body", "plain", "utf-8"))

try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5) as server:
        server.set_debuglevel(1)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        print("Success")
except Exception as e:
    print(f"Error: {e}")
