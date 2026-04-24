from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from api.deps import get_db, require_user
from shared.auth import create_magic_link, exchange_magic_link, revoke_session

router = APIRouter(prefix="/auth", tags=["auth"])


class MagicLinkStartRequest(BaseModel):
    email: str


class MagicLinkCompleteRequest(BaseModel):
    token: str


@router.post("/magic-link/start")
def start_magic_link(req: MagicLinkStartRequest, conn=Depends(get_db)):
    token = create_magic_link(conn, req.email)
    return {
        "status": "sent",
        "email": req.email,
        "dev_magic_link_token": token,
    }


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


@router.get("/me")
def get_me(user: dict = Depends(require_user)):
    return {"user": user}


@router.get("/health")
def auth_health():
    raise HTTPException(status_code=404, detail="Use /health instead")
