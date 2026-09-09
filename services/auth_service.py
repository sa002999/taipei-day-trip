import os
from typing import Any

import jwt
from dotenv import load_dotenv
from passlib.context import CryptContext

from database import (
    create_member,
    get_member_by_email,
    get_member_by_id,
)

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class InvalidCredentialsError(Exception):
    pass


class AuthConfigurationError(Exception):
    pass


def register_member(name: str, email: str, password: str) -> None:
    normalized_name = name.strip()
    normalized_email = email.strip().lower()

    if not normalized_name or not normalized_email or not password:
        raise ValueError("姓名、Email 和密碼不可為空")
    if get_member_by_email(normalized_email) is not None:
        raise ValueError("Email 已被註冊")

    create_member(
        normalized_name,
        normalized_email,
        password_context.hash(password),
    )


def login_member(email: str, password: str) -> str:
    normalized_email = email.strip().lower()
    member = get_member_by_email(normalized_email)

    if member is None or not password_context.verify(password, member["password_hash"]):
        raise InvalidCredentialsError

    if not JWT_SECRET_KEY:
        raise AuthConfigurationError

    payload = {
        "id": member["id"],
        "name": member["name"],
        "email": member["email"],
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_member(authorization: str | None) -> dict[str, Any] | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    if not JWT_SECRET_KEY:
        return None

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        member_id = payload.get("id")
        if not isinstance(member_id, int):
            return None
        return get_member_by_id(member_id)
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
