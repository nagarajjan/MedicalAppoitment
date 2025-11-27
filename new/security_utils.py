from passlib.context import CryptContext
import re

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def validate_password_complexity(password: str) -> bool:
    # Relaxed regex for ease of use in demo, stricter in production
    if len(password) < 4: return False 
    return True