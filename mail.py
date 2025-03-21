import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import os
from dotenv import load_dotenv
load_dotenv()
# Hard-coded sender and recipient information
print(os.getenv("SAMPLE"))
SENDER_EMAIL = os.getenv("MAIL_ID")  # Replace with your Gmail address
SENDER_PASSWORD = os.getenv("MAIL_PASSWORD")   # Replace with your App Password (not your regular Gmail password)
RECIPIENT_EMAILS = ["msk17092002@gmail.com"]  # Replace with recipient email addresses

# Email content
SUBJECT = "Automated Email"
BODY = """
Hello,

This is an automated email sent from my Python script without opening Gmail.

Best regards,
Your Name
"""

def send_email():
    """Function to send an email using Gmail SMTP"""
    # Create the email message
    message = MIMEMultipart()
    message["From"] = SENDER_EMAIL
    message["To"] = ", ".join(RECIPIENT_EMAILS)
    message["Subject"] = SUBJECT
    
    # Attach the body of the email
    message.attach(MIMEText(BODY, "plain"))
    
    try:
        # Create SMTP session
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # Enable security
        
        # Login to your Gmail account
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        # Send the email
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAILS, message.as_string())
        
        # Close the SMTP session
        server.quit()
        
        print(f"Email successfully sent to {', '.join(RECIPIENT_EMAILS)}")
        return True
    
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

if __name__ == "__main__":
    send_email()