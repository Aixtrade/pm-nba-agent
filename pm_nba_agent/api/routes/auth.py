"""认证路由"""

from fastapi import APIRouter, HTTPException

from ..models.requests import LoginRequest, LoginResponse
from ..services.auth import derive_token, get_auth_config


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """口令登录，返回长期 Token"""
    passphrase, salt = get_auth_config()

    if not passphrase:
        raise HTTPException(status_code=500, detail="Auth 配置缺失")

    if body.passphrase != passphrase:
        raise HTTPException(status_code=401, detail="口令不正确")

    token = derive_token(passphrase, salt)
    return LoginResponse(token=token)
