import os
import uuid
import base64
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import TypeDecorator, String
from sqlalchemy.orm import Mapped, mapped_column
from typing import List
from app.extensions import db

ENCRYPTION_KEY_ENV_VAR = 'WORKSHOP_AI_ENCRYPTION_KEY'
_fernet_instance = None

def get_fernet():
    global _fernet_instance
    if _fernet_instance is None:
        try:
            key = os.environ[ENCRYPTION_KEY_ENV_VAR]
            key_bytes = key.encode()
            base64.urlsafe_b64decode(key_bytes)
            _fernet_instance = Fernet(key_bytes)
        except KeyError:
            print(f"WARNING: Environment variable {ENCRYPTION_KEY_ENV_VAR} not set. API keys will NOT be encrypted.")
            class DummyFernet:
                def encrypt(self, data): return data
                def decrypt(self, token): return token
            _fernet_instance = DummyFernet()
        except (ValueError, TypeError) as e:
             raise ValueError(f"Invalid encryption key format in {ENCRYPTION_KEY_ENV_VAR}: {e}. Ensure it's a valid URL-safe base64 encoded key.")
    return _fernet_instance

class EncryptedString(TypeDecorator):
    """Encrypts/Decrypts a string value for storage in the database using Fernet."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value: str, dialect):
        """Encrypt data on the way in."""
        if value is not None:
            fernet = get_fernet()
            value_bytes = value.encode()
            encrypted_value = fernet.encrypt(value_bytes)
            return encrypted_value.decode()
        return value

    def process_result_value(self, value: str, dialect):
        """Decrypt data on the way out."""
        if value is not None:
            fernet = get_fernet()
            try:
                value_bytes = value.encode()
                decrypted_value = fernet.decrypt(value_bytes)
                return decrypted_value.decode()
            except InvalidToken:
                print("Warning: Could not decrypt value. It might have been encrypted with a different key or is corrupted.")
                return None
            except Exception as e:
                print(f"Error decrypting value: {e}")
                return None
        return value

class Api(db.Model):
    """Represents an API configuration stored in the database."""
    __tablename__ = 'apis'

    id: Mapped[str] = mapped_column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(db.String, nullable=False, index=True)
    api_type: Mapped[str] = mapped_column(db.String, nullable=False, index=True)
    source: Mapped[str] = mapped_column(db.String, nullable=False, index=True)
    api_url: Mapped[str] = mapped_column(db.String, nullable=False)
    api_key: Mapped[EncryptedString] = mapped_column(EncryptedString, nullable=False)
    model: Mapped[str] = mapped_column(db.String, nullable=False, index=True)
    tags: Mapped[List[str]] = mapped_column(db.JSON, nullable=False, default=lambda: ['default'])