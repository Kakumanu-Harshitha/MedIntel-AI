import os
import pyotp
import qrcode
import base64
from io import BytesIO
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# We need a stable key for encryption/decryption of the TOTP secret.
# If TOTP_ENCRYPTION_KEY is not in .env, we'll generate one but it won't persist across restarts.
ENCRYPTION_KEY = os.getenv("TOTP_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # In a real production app, this must be in .env
    # For now, we generate one to avoid crashes, but warn the user.
    print("WARNING: TOTP_ENCRYPTION_KEY not set in .env. TOTP secrets will not be decryptable after restart.")
    ENCRYPTION_KEY = Fernet.generate_key().decode()

fernet = Fernet(ENCRYPTION_KEY.encode())

class TOTPUtility:
    @staticmethod
    def generate_secret() -> str:
        """Generates a base32 secret for TOTP."""
        return pyotp.random_base32()

    @staticmethod
    def encrypt_secret(secret: str) -> str:
        """Encrypts the TOTP secret for database storage."""
        return fernet.encrypt(secret.encode()).decode()

    @staticmethod
    def decrypt_secret(encrypted_secret: str) -> str:
        """Decrypts the TOTP secret for verification."""
        return fernet.decrypt(encrypted_secret.encode()).decode()

    @staticmethod
    def get_provisioning_uri(secret: str, email: str, issuer: str = "AIHealthAssistant") -> str:
        """Creates the otpauth URI for QR code generation."""
        return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)

    @staticmethod
    def generate_qr_base64(provisioning_uri: str) -> str:
        """Generates a base64 encoded QR code image from the provisioning URI."""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"

    @staticmethod
    def verify_otp(secret: str, otp: str) -> bool:
        """Verifies the 6-digit OTP using RFC 6238."""
        totp = pyotp.TOTP(secret)
        # valid_window=1 allows ±30 seconds clock drift
        return totp.verify(otp, valid_window=1)
