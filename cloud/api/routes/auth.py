import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, field_validator

from api.deps import get_db
from shared.auth import (
    exchange_magic_link,
    issue_magic_link_or_none,
    magic_link_token_may_appear_in_json,
    normalize_email,
    revoke_session,
)
from shared.config import settings as cloud_settings
from shared.magic_link_mail import send_magic_link_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class MagicLinkStartRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


class MagicLinkCompleteRequest(BaseModel):
    token: str

    @field_validator("token", mode="before")
    @classmethod
    def strip_token(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


@router.post("/magic-link/start")
def start_magic_link(req: MagicLinkStartRequest, conn=Depends(get_db)):
    norm = normalize_email(str(req.email))
    token = issue_magic_link_or_none(conn, str(req.email))
    body: dict = {"status": "sent", "email": norm}
    if token:
        mailed = send_magic_link_email(norm, token)
        if mailed:
            body["delivery"] = "email"
        elif cloud_settings.resend_api_key:
            body["delivery"] = "email_failed"
            logger.error(
                "Magic link email failed for %s (token still valid until used)", norm
            )
        elif not magic_link_token_may_appear_in_json():
            logger.warning(
                "Magic link issued for %s but email not configured (set CIH_CLOUD_RESEND_API_KEY)",
                norm,
            )
        if magic_link_token_may_appear_in_json():
            body["dev_magic_link_token"] = token
    return body


@router.post("/magic-link/complete")
def complete_magic_link(req: MagicLinkCompleteRequest, conn=Depends(get_db)):
    return exchange_magic_link(conn, req.token)


@router.post("/logout", status_code=204)
def logout(
    authorization: str | None = Header(default=None),
    conn=Depends(get_db),
):
    if authorization and authorization.startswith("Bearer "):
        revoke_session(conn, authorization.removeprefix("Bearer ").strip())
    return None


@router.get("/health")
def auth_health():
    raise HTTPException(status_code=404, detail="Use /health instead")
