import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv("GMAIL_SENDER_EMAIL")
        self.sender_password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    def send_password_reset_email(self, target_email: str, token: str):
        """
        Sends a secure password reset link via Gmail SMTP.
        """
        # Reload credentials from environment to catch changes without restart
        load_dotenv()
        sender_email = os.getenv("GMAIL_SENDER_EMAIL")
        sender_password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        if not sender_email or not sender_password:
            print("⚠️ WARNING: Gmail credentials missing in .env. Cannot send email.")
            return False

        try:
            # 1. Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = "Password Reset Request - AI Health Assistant"
            message["From"] = f"AI Health Assistant <{sender_email}>"
            message["To"] = target_email

            reset_link = f"{frontend_url}/reset-password?token={token}"

            # 2. Email Body (Non-technical & Clear)
            text = f"""
            Hello,

            We received a request to reset your password for your AI Health Assistant account.
            
            Click the link below to set a new password:
            {reset_link}

            This link will expire in 15 minutes for your security.
            If you did not request this change, please ignore this email.

            Stay healthy,
            AI Health Assistant Team
            """

            html = f"""
            <html>
              <body style="font-family: sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                  <h2 style="color: #2D6A4F;">Password Reset Request</h2>
                  <p>Hello,</p>
                  <p>We received a request to reset your password for your AI Health Assistant account.</p>
                  <p style="margin: 30px 0;">
                    <a href="{reset_link}" style="background-color: #2D6A4F; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
                  </p>
                  <p style="font-size: 0.9em; color: #666;">
                    This link will expire in <strong>15 minutes</strong> for your security.
                  </p>
                  <p style="font-size: 0.9em; color: #666;">
                    If you did not request this change, please ignore this email.
                  </p>
                  <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                  <p style="font-size: 0.8em; color: #999;">
                    AI Health Assistant - Secure Healthcare MVP
                  </p>
                </div>
              </body>
            </html>
            """

            # 3. Attach parts
            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")
            message.attach(part1)
            message.attach(part2)

            # 4. Connect and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Secure the connection
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, target_email, message.as_string())
            
            print(f"📧 Password reset email sent to {target_email}")
            return True

        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False

email_service = EmailService()
