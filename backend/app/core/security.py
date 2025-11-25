import bcrypt


def hash_password(plain_password: str) -> str:
    """
    Hash a password using bcrypt.
    Bcrypt has a maximum password length of 72 bytes, so we truncate if necessary.
    """
    password_bytes = plain_password.encode('utf-8')
    
    # Bcrypt has a maximum password length of 72 bytes
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Generate salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return as string for storage in database
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a bcrypt hash.
    """
    password_bytes = plain_password.encode('utf-8')
    
    # Bcrypt has a maximum password length of 72 bytes
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    hashed_bytes = hashed_password.encode('utf-8')
    
    return bcrypt.checkpw(password_bytes, hashed_bytes)
