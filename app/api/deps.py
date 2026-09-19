from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import gettext_for, normalize_locale
from app.core.security import decode_access_token
from app.db import get_session
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительные учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials if credentials else access_token
    if token is None:
        raise unauthorized

    user_id = decode_access_token(token)
    if user_id is None:
        raise unauthorized

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    session: SessionDep,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User | None:
    if access_token is None:
        return None
    user_id = decode_access_token(access_token)
    if user_id is None:
        return None
    user = await session.get(User, user_id)
    return user if user and user.is_active else None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


async def get_locale(
    lang: Annotated[str | None, Cookie()] = None,
    accept_language: Annotated[str | None, Header()] = None,
) -> str:
    if lang:
        return normalize_locale(lang)
    return normalize_locale(accept_language)


LocaleDep = Annotated[str, Depends(get_locale)]


async def get_translator(locale: LocaleDep):
    return gettext_for(locale)


TranslatorDep = Annotated[object, Depends(get_translator)]
