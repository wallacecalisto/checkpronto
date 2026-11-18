from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user_allow_password_change
from app.core.rate_limit import enforce_login_rate_limit
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    hash_secret,
    verify_secret,
)
from app.db.session import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse, UserPublic
from app.services import audit_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos."
)
_INVALID_SESSION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada."
)
_INVALID_CURRENT_PASSWORD = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Senha atual incorreta.", "code": "INVALID_CURRENT_PASSWORD"},
)


def _refresh_token_expire_days(role: str) -> int:
    if role == "OPERACIONAL":
        return settings.operational_refresh_token_expire_days
    return settings.refresh_token_expire_days


def _set_refresh_cookie(response: Response, raw_refresh_token: str, expire_days: int) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=expire_days * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
    )


def _issue_tokens(user: User, db: Session, response: Response) -> TokenResponse:
    access_token = create_access_token(user_id=user.id, role=user.role, store_id=user.store_id)
    expire_days = _refresh_token_expire_days(user.role)

    raw_refresh_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=expire_days),
        )
    )
    db.commit()

    _set_refresh_cookie(response, raw_refresh_token, expire_days)
    return TokenResponse(access_token=access_token, user=UserPublic.model_validate(user))


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(enforce_login_rate_limit)])
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))

    if user is None or not user.active or not verify_secret(payload.password, user.password_hash):
        raise _INVALID_CREDENTIALS

    return _issue_tokens(user, db, response)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh_token is None:
        raise _INVALID_SESSION

    token_hash = hash_refresh_token(raw_refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    now = datetime.now(timezone.utc)
    if stored is None or stored.revoked_at is not None or stored.expires_at < now:
        raise _INVALID_SESSION

    user = db.get(User, stored.user_id)
    if user is None or not user.active:
        raise _INVALID_SESSION

    stored.revoked_at = now
    db.add(stored)

    return _issue_tokens(user, db, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if raw_refresh_token is not None:
        token_hash = hash_refresh_token(raw_refresh_token)
        stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = datetime.now(timezone.utc)
            db.add(stored)
            db.commit()

    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@router.post(
    "/change-password", response_model=UserPublic, dependencies=[Depends(enforce_login_rate_limit)]
)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_allow_password_change),
) -> UserPublic:
    if not verify_secret(payload.current_password, current_user.password_hash):
        raise _INVALID_CURRENT_PASSWORD

    current_user.password_hash = hash_secret(payload.new_password)
    current_user.must_change_password = False
    db.add(current_user)

    audit_service.log(
        db,
        store_id=current_user.store_id,
        action="RESET_PASSWORD",
        entity_type="USER",
        entity_id=current_user.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
    )

    db.commit()
    db.refresh(current_user)
    return UserPublic.model_validate(current_user)
