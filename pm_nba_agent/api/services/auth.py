"""认证相关工具"""

import hashlib
import hmac
import os

from fastapi import HTTPException, Request


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


def require_auth(request: Request) -> None:
    passphrase, salt = get_auth_config()

    if not passphrase:
        raise HTTPException(status_code=500, detail="Auth 配置缺失")

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少访问令牌")

    provided = auth_header.removeprefix("Bearer ").strip()
    if not is_token_valid(provided, passphrase, salt):
        raise HTTPException(status_code=401, detail="访问令牌无效")
