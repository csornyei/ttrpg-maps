from secrets import compare_digest

from fastapi import Depends, Header, HTTPException, status

from src.config import Settings, get_settings


def require_write_auth(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    provided_token: str | None = None

    if authorization and authorization.lower().startswith("bearer "):
        provided_token = authorization[7:].strip()
    elif x_api_key:
        provided_token = x_api_key.strip()

    if not provided_token or not compare_digest(provided_token, settings.api_auth_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
