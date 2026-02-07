"""多用户 JWT 认证服务"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import yaml
from fastapi import HTTPException, Request
from loguru import logger


# ── 模块级缓存 ──────────────────────────────────────────────

_users: dict[str, str] | None = None  # {username: password}


def _get_jwt_secret() -> str:
    """获取 JWT 签名密钥"""
    secret = os.getenv("JWT_SECRET") or os.getenv("LOGIN_PASSPHRASE") or ""
    if not secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET 未配置")
    return secret


# ── 用户管理 ────────────────────────────────────────────────

def load_users(path: str | None = None) -> dict[str, str]:
    """从 YAML 加载用户列表，返回 {username: password}"""
    global _users

    if path is None:
        path = os.getenv("USERS_CONFIG_PATH", "config/users.yaml")

    p = Path(path)
    if not p.is_file():
        logger.warning("用户配置文件不存在: {}，回退到环境变量单用户模式", path)
        # 向后兼容：如果没有 YAML，用 LOGIN_PASSPHRASE 作为 admin 密码
        passphrase = os.getenv("LOGIN_PASSPHRASE", "")
        if passphrase:
            _users = {"admin": passphrase}
        else:
            _users = {}
        return _users

    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    user_list = data.get("users") or []
    _users = {}
    for entry in user_list:
        username = str(entry.get("username", "")).strip()
        password = str(entry.get("password", ""))
        if username and password:
            _users[username] = password

    logger.info("已加载 {} 个用户账号", len(_users))
    return _users


def reload_users() -> dict[str, str]:
    """重新加载用户列表"""
    global _users
    _users = None
    return load_users()


def _get_users() -> dict[str, str]:
    """获取已缓存的用户列表（首次自动加载）"""
    global _users
    if _users is None:
        load_users()
    return _users  # type: ignore[return-value]


def verify_user(username: str, password: str) -> bool:
    """验证用户名和密码"""
    users = _get_users()
    expected = users.get(username)
    if expected is None:
        return False
    return expected == password


# ── JWT ─────────────────────────────────────────────────────

_JWT_ALGORITHM = "HS256"
_JWT_EXPIRE_DAYS = 7


def create_jwt(username: str) -> str:
    """创建 JWT，payload: {sub: username, exp: now+7d}"""
    secret = _get_jwt_secret()
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=_JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, secret, algorithm=_JWT_ALGORITHM)


def decode_jwt(token: str) -> str:
    """解码 JWT，返回 username。无效/过期时抛出 HTTPException 401"""
    secret = _get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[_JWT_ALGORITHM])
        username: str = payload.get("sub", "")
        if not username:
            raise HTTPException(status_code=401, detail="无效的令牌")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="令牌已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的令牌")


# ── FastAPI 依赖 ────────────────────────────────────────────

def require_auth(request: Request) -> str:
    """从 Bearer token 解码 JWT，返回 username。失败抛 401"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少访问令牌")

    token = auth_header.removeprefix("Bearer ").strip()
    return decode_jwt(token)
