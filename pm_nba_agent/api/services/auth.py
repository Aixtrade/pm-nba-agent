"""认证相关工具"""

import hashlib
import hmac
import os


def get_auth_config() -> tuple[str, str]:
    passphrase = os.getenv("LOGIN_PASSPHRASE", "")
    salt = os.getenv("LOGIN_TOKEN_SALT", "")
    return passphrase, salt


def derive_token(passphrase: str, salt: str) -> str:
    if not passphrase:
        return ""
    message = passphrase.encode("utf-8")
    key = salt.encode("utf-8") if salt else b"pm_nba_agent"
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def is_token_valid(token: str, passphrase: str, salt: str) -> bool:
    expected = derive_token(passphrase, salt)
    if not expected or not token:
        return False
    return hmac.compare_digest(token, expected)
