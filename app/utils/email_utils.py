import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(subject, recipient, body, smtp_server='smtp.gmail.com', smtp_port=587, sender_email='your_email@gmail.com', sender_password='your_password'):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient, msg.as_string())
        server.quit()
        print(f"[Email] Envoyé à {recipient}")
        return True
    except Exception as e:
        print(f"[Email Error] {e}")
        return False
