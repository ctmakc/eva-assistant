"""Authentication and authorization for EVA API."""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import get_settings

logger = logging.getLogger("eva.auth")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
security = HTTPBearer(auto_error=False)

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 1 week


class AuthManager:
    """Manages authentication state and admin credentials."""

    def __init__(self):
        settings = get_settings()
        self.data_dir = os.path.join(settings.data_dir, "auth")
        os.makedirs(self.data_dir, exist_ok=True)
        self.auth_file = os.path.join(self.data_dir, "admin.json")
        self._load()

    def _load(self):
        """Load auth data from file."""
        if os.path.exists(self.auth_file):
            with open(self.auth_file, 'r') as f:
                self._data = json.load(f)
        else:
            self._data = {
                "initialized": False,
                "admin_password_hash": None,
                "setup_completed": False
            }

    def _save(self):
        """Save auth data to file."""
        with open(self.auth_file, 'w') as f:
            json.dump(self._data, f)

    @property
    def is_initialized(self) -> bool:
        """Check if admin account is set up."""
        return self._data.get("initialized", False)

    def setup_admin(self, password: str) -> bool:
        """
        Initial admin setup. Only works once.
        """
        if self.is_initialized:
            return False

        self._data["admin_password_hash"] = pwd_context.hash(password)
        self._data["initialized"] = True
        self._data["setup_completed"] = True
        self._data["setup_at"] = datetime.now().isoformat()
        self._save()

        logger.info("Admin account initialized")
        return True

    def verify_password(self, password: str) -> bool:
        """Verify admin password."""
        if not self.is_initialized:
            # Allow default password from env for initial setup
            settings = get_settings()
            if settings.admin_password and password == settings.admin_password:
                return True
            return False

        stored_hash = self._data.get("admin_password_hash")
        if not stored_hash:
            return False

        return pwd_context.verify(password, stored_hash)

    def change_password(self, old_password: str, new_password: str) -> bool:
        """Change admin password."""
        if not self.verify_password(old_password):
            return False

        self._data["admin_password_hash"] = pwd_context.hash(new_password)
        self._data["password_changed_at"] = datetime.now().isoformat()
        self._save()

        logger.info("Admin password changed")
        return True

    def create_access_token(self) -> str:
        """Create JWT access token."""
        settings = get_settings()
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

        to_encode = {
            "sub": "admin",
            "exp": expire,
            "iat": datetime.utcnow()
        }

        return jwt.encode(to_encode, settings.api_secret_key, algorithm=ALGORITHM)

    def verify_token(self, token: str) -> bool:
        """Verify JWT token."""
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.api_secret_key, algorithms=[ALGORITHM])
            return payload.get("sub") == "admin"
        except JWTError:
            return False


# Singleton
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


# Dependency for protected routes
async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """Dependency that requires valid authentication."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth = get_auth_manager()
    if not auth.verify_token(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


# Optional auth - doesn't fail if no token, just returns False
async def optional_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """Optional authentication - returns True if valid, False otherwise."""
    if credentials is None:
        return False

    auth = get_auth_manager()
    return auth.verify_token(credentials.credentials)
