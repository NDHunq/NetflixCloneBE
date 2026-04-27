from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    phone_number: str
    password: str


class RegisterRequest(BaseModel):
    phone_number: str
    full_name: str
    password: str
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    phone_number: str
    full_name: str
    profile_id: Optional[str] = None
    profile_name: Optional[str] = None
    created_at: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    user: UserResponse


class OIDCTokenExchangeRequest(BaseModel):
    grant_type: str
    client_id: str
    code: str
    redirect_uri: str
    code_verifier: str


class SSOIdentityResponse(BaseModel):
    provider: str
    subject: str
    profile_id: str
    audience: Optional[str] = None
    full_name: Optional[str] = None
    gender: Optional[str] = None
    local_user_id: int
    last_login_at: Optional[str] = None


class OIDCTokenExchangeResponse(BaseModel):
    app_access_token: str
    app_token_type: str = "Bearer"
    app_expires_in_seconds: int
    user: UserResponse
    identity: SSOIdentityResponse
    # Keep upstream fields for compatibility/debug in demo.
    upstream_access_token: str
    upstream_id_token: str
    upstream_token_type: str
    upstream_expires_in: int
