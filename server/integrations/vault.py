"""Secure credential vault for storing service credentials."""

import os
import json
import base64
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import get_settings

logger = logging.getLogger("eva.vault")


class CredentialVault:
    """
    Encrypted storage for service credentials.

    Supports dynamic credential addition:
    "EVA, вот логин-пароль для Reddit" -> stores encrypted
    """

    def __init__(self):
        settings = get_settings()
        self.data_dir = os.path.join(settings.data_dir, "credentials")
        os.makedirs(self.data_dir, exist_ok=True)

        # Derive encryption key from master key
        self._fernet = self._create_fernet(settings.vault_master_key)
        self._credentials: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    def _create_fernet(self, master_key: str) -> Fernet:
        """Create Fernet cipher from master key."""
        # Use PBKDF2 to derive a proper key from the master key
        salt = b'eva_vault_salt_v1'  # Fixed salt (ok for this use case)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)

    def _get_file_path(self, service: str) -> str:
        """Get encrypted file path for a service."""
        return os.path.join(self.data_dir, f"{service}.enc")

    def _load_all(self):
        """Load all stored credentials into memory."""
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.enc'):
                service = filename[:-4]
                try:
                    self._credentials[service] = self._load_service(service)
                except Exception as e:
                    logger.error(f"Failed to load credentials for {service}: {e}")

    def _load_service(self, service: str) -> Dict[str, Any]:
        """Load and decrypt credentials for a service."""
        file_path = self._get_file_path(service)
        if not os.path.exists(file_path):
            return {}

        with open(file_path, 'rb') as f:
            encrypted_data = f.read()

        decrypted = self._fernet.decrypt(encrypted_data)
        return json.loads(decrypted.decode())

    def _save_service(self, service: str, data: Dict[str, Any]):
        """Encrypt and save credentials for a service."""
        file_path = self._get_file_path(service)
        json_data = json.dumps(data).encode()
        encrypted = self._fernet.encrypt(json_data)

        with open(file_path, 'wb') as f:
            f.write(encrypted)

    def store(self, service: str, credentials: Dict[str, str], metadata: Dict = None):
        """
        Store credentials for a service.

        Args:
            service: Service name (e.g., 'reddit', 'gmail', 'twitter')
            credentials: Dict with credential data (username, password, token, etc.)
            metadata: Optional metadata (added_at, notes, etc.)
        """
        data = {
            "credentials": credentials,
            "metadata": metadata or {},
            "added_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        self._credentials[service] = data
        self._save_service(service, data)
        logger.info(f"Stored credentials for {service}")

    def get(self, service: str) -> Optional[Dict[str, str]]:
        """Get credentials for a service."""
        if service in self._credentials:
            return self._credentials[service].get("credentials")
        return None

    def get_with_metadata(self, service: str) -> Optional[Dict[str, Any]]:
        """Get credentials with metadata."""
        return self._credentials.get(service)

    def has(self, service: str) -> bool:
        """Check if credentials exist for a service."""
        return service in self._credentials

    def delete(self, service: str) -> bool:
        """Delete credentials for a service."""
        if service in self._credentials:
            del self._credentials[service]
            file_path = self._get_file_path(service)
            if os.path.exists(file_path):
                os.unlink(file_path)
            logger.info(f"Deleted credentials for {service}")
            return True
        return False

    def list_services(self) -> list:
        """List all services with stored credentials."""
        return list(self._credentials.keys())

    def update(self, service: str, credentials: Dict[str, str]):
        """Update existing credentials."""
        if service in self._credentials:
            self._credentials[service]["credentials"].update(credentials)
            self._credentials[service]["updated_at"] = datetime.now().isoformat()
            self._save_service(service, self._credentials[service])
            logger.info(f"Updated credentials for {service}")
        else:
            self.store(service, credentials)


# Singleton
_vault: Optional[CredentialVault] = None


def get_vault() -> CredentialVault:
    global _vault
    if _vault is None:
        _vault = CredentialVault()
    return _vault
