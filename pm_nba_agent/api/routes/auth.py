"""认证路由"""

from fastapi import APIRouter, HTTPException

from ..models.requests import LoginRequest, LoginResponse
from ..services.auth import verify_user, create_jwt


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """用户名 + 密码登录，返回 JWT"""
    if not verify_user(body.username, body.password):
        raise HTTPException(status_code=401, detail="用户名或密码不正确")

    token = create_jwt(body.username)
    return LoginResponse(token=token, username=body.username)
