import requests
import logging
from datetime import datetime, timezone
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import Config
from app.core.security import SecurityManager, get_current_user
from app.db.database import get_db
from app.models.user import User, create_sso_user, create_user, get_user_by_id, get_user_by_phone, get_user_by_profile
from app.models.sso_identity import get_identity, upsert_identity
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    OIDCTokenExchangeResponse,
    OIDCTokenExchangeRequest,
    RegisterRequest,
    UserResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("sso.netflix_be")


def _short(value: str, head: int = 8) -> str:
    return value[:head] if value else "nil"


def _decode_upstream_claims_without_signature(id_token: str) -> dict:
    # NOTE: For full production hardening, verify RS256 signature via JWKS/public key.
    # This demo implementation validates critical claims while trusting backend-to-backend transport.
    claims = jwt.decode(
        id_token,
        options={
            "verify_signature": False,
            "verify_exp": False,
            "verify_aud": False,
        },
        algorithms=["RS256", "HS256"],
    )
    return claims


@router.post("/register", response_model=LoginResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = get_user_by_phone(db, payload.phone_number)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Số điện thoại đã được sử dụng",
        )

    user = create_user(
        db=db,
        phone_number=payload.phone_number,
        full_name=payload.full_name,
        password=payload.password,
    )
    token = SecurityManager.create_token(user.id)

    return {
        "access_token": token,
        "user": user.to_dict(),
    }


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_phone(db, payload.phone_number)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.verify_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    token = SecurityManager.create_token(user.id)
    return {
        "access_token": token,
        "user": user.to_dict(),
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user.to_dict()


@router.post("/oidc/token", response_model=OIDCTokenExchangeResponse)
def oidc_token_exchange(payload: OIDCTokenExchangeRequest, db: Session = Depends(get_db)):
    super_app_token_url = f"{Config.SUPER_APP_BE_URL}/oidc/token"

    logger.info(
        "[SSO][NetflixBE][TokenProxy] status=request client_id=%s code_head=%s redirect_uri=%s verifier_len=%s upstream=%s",
        payload.client_id,
        _short(payload.code),
        payload.redirect_uri,
        len(payload.code_verifier or ""),
        super_app_token_url,
    )

    try:
        response = requests.post(super_app_token_url, json=payload.model_dump(), timeout=15)
    except requests.RequestException as exc:
        logger.exception("[SSO][NetflixBE][TokenProxy] status=failed reason=upstream_request_exception")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to call SuperApp BE: {exc}",
        )

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        body = response.json()
    else:
        body = {"error": response.text or "Unknown error"}

    if response.status_code >= 400:
        logger.warning(
            "[SSO][NetflixBE][TokenProxy] status=upstream_error status_code=%s body=%s",
            response.status_code,
            body,
        )
        return JSONResponse(status_code=response.status_code, content=body)

    logger.info(
        "[SSO][NetflixBE][TokenProxy] status=upstream_ok status_code=%s has_access_token=%s has_id_token=%s token_type=%s expires_in=%s",
        response.status_code,
        bool(body.get("access_token")),
        bool(body.get("id_token")),
        body.get("token_type", "Bearer"),
        body.get("expires_in", 0),
    )

    # -------- Model B mapping: one Netflix account per (sub, profile_id) --------
    id_token = body.get("id_token", "")
    if not id_token:
        logger.warning("[SSO][NetflixBE][TokenProxy] status=failed reason=missing_id_token")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Upstream missing id_token")

    try:
        claims = _decode_upstream_claims_without_signature(id_token)
    except Exception as exc:
        logger.exception("[SSO][NetflixBE][TokenProxy] status=failed reason=decode_id_token")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Invalid id_token: {exc}")

    subject = claims.get("sub")
    profile_id = claims.get("profile_id")
    audience = claims.get("aud")
    user_full_name = claims.get("user_full_name") or claims.get("full_name")
    user_phone_number = claims.get("user_phone_number")
    profile_display_name = claims.get("profile_display_name") or claims.get("full_name")
    gender = claims.get("gender")
    exp = claims.get("exp")

    logger.info(
        "[SSO][NetflixBE][Claims] sub_head=%s profile_id=%s aud=%s exp=%s user_full_name=%s user_phone=%s profile_display_name=%s gender=%s",
        _short(subject or ""),
        profile_id or "nil",
        audience or "nil",
        exp,
        user_full_name or "nil",
        user_phone_number or "nil",
        profile_display_name or "nil",
        gender or "nil",
    )

    if not subject or not profile_id:
        logger.warning("[SSO][NetflixBE][TokenProxy] status=failed reason=missing_subject_or_profile")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing sub/profile_id in id_token")

    if audience != Config.SERVICE_APP_CLIENT_ID:
        logger.warning(
            "[SSO][NetflixBE][TokenProxy] status=failed reason=aud_mismatch expected=%s got=%s",
            Config.SERVICE_APP_CLIENT_ID,
            audience,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audience mismatch")

    if not isinstance(exp, int) or exp < int(datetime.now(timezone.utc).timestamp()):
        logger.warning("[SSO][NetflixBE][TokenProxy] status=failed reason=token_expired_or_invalid_exp")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")

    provider = "superapp"
    
    # Model B: One Netflix user per (phone_number, SuperApp_profile_id) tuple
    identity = get_identity(db, provider=provider, subject=subject, profile_id=profile_id)

    logger.info(
        "[SSO][NetflixBE][Map] status=lookup provider=%s sub_head=%s profile_id=%s identity_found=%s",
        provider,
        _short(subject),
        profile_id,
        bool(identity),
    )

    if identity:
        # Identity already exists - reuse local_user
        local_user = get_user_by_id(db, identity.local_user_id)
        if not local_user:
            logger.error(
                "[SSO][NetflixBE][Map] status=error reason=identity_points_to_missing_user identity_id=%s",
                identity.id,
            )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User data corrupted")
        
        logger.info(
            "[SSO][NetflixBE][Map] status=existing provider=%s sub_head=%s profile_id=%s local_user_id=%s",
            provider,
            _short(subject),
            profile_id,
            local_user.id,
        )
    else:
        # First login for this profile - create new Netflix user
        local_user = create_sso_user(
            db,
            provider=provider,
            subject=subject,
            profile_id=profile_id,
            full_name=user_full_name or "SSO User",
            profile_name=profile_display_name or "Profile",
            phone_number=user_phone_number or f"sso_{subject[:8]}",
        )
        logger.info(
            "[SSO][NetflixBE][Map] status=created provider=%s sub_head=%s profile_id=%s local_user_id=%s phone=%s profile_name=%s",
            provider,
            _short(subject),
            profile_id,
            local_user.id,
            local_user.phone_number,
            local_user.profile_name,
        )

    identity = upsert_identity(
        db,
        provider=provider,
        subject=subject,
        profile_id=profile_id,
        audience=audience,
        full_name=profile_display_name,
        gender=gender,
        local_user_id=local_user.id,
    )

    logger.info(
        "[SSO][NetflixBE][Map] status=upsert identity_local_user_id=%s audience=%s last_login_at=%s",
        identity.local_user_id,
        identity.audience or "nil",
        identity.last_login_at.isoformat() if identity.last_login_at else "nil",
    )

    app_access_token = SecurityManager.create_token(local_user.id)

    logger.info(
        "[SSO][NetflixBE][TokenProxy] status=ok status_code=%s upstream_access_token_head=%s app_access_token_head=%s local_user_id=%s profile_id=%s",
        response.status_code,
        _short(body.get("access_token", "")),
        _short(app_access_token),
        local_user.id,
        profile_id,
    )

    return {
        "app_access_token": app_access_token,
        "app_token_type": "Bearer",
        "app_expires_in_seconds": int(Config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds()),
        "user": local_user.to_dict(),
        "identity": identity.to_dict(),
        "upstream_access_token": body.get("access_token", ""),
        "upstream_id_token": body.get("id_token", ""),
        "upstream_token_type": body.get("token_type", "Bearer"),
        "upstream_expires_in": body.get("expires_in", 0),
    }
