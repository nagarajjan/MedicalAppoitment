from passlib.context import CryptContext
import re

# Use pbkdf2_sha256 to avoid Bcrypt's 72-byte limitation and Windows issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def validate_password_complexity(password: str) -> bool:
    """Min 8, Max 10, Alphanumeric + Special Char"""
    if len(password) < 8 or len(password) > 10:
        return False
    if not re.match(r'^[a-zA-Z0-9@#$%&*]+$', password):
        return False
    if not re.search(r'[@#$%&*]', password):
        return False
    if not re.search(r'[a-zA-Z0-9]', password):
        return False
    return True