import os
import re
import time
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from psycopg.errors import UniqueViolation

from app.db import get_connection
from app.errors import ApiError
from app.identity import current_user_claims
from app.security import create_access_token, hash_password, verify_password

users_router = APIRouter(prefix="/api/v1/users", tags=["Users"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_phase_cache = {"phase": "expand", "timestamp": 0.0}
_connection = get_connection


def split_name(name: str) -> tuple[str, str]:
    cleaned = name.strip()
    parts = cleaned.split(maxsplit=1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def get_migration_phase(conn: psycopg.Connection | None = None) -> str:
    now = time.time()
    if now - _phase_cache["timestamp"] < 1.0:
        return _phase_cache["phase"]

    def _query(c: psycopg.Connection) -> str:
        try:
            row = c.execute("SELECT phase FROM migration_state WHERE name = 'user_names'").fetchone()
            return row["phase"] if row and "phase" in row else "expand"
        except Exception:
            return "expand"

    if conn is not None:
        phase = _query(conn)
    else:
        with get_connection() as c:
            phase = _query(c)

    _phase_cache["phase"] = phase
    _phase_cache["timestamp"] = now
    return phase


class UserRegisterInput(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["customer", "rider"] = "customer"

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, value: str) -> str:
        value = value.strip()
        if not EMAIL_REGEX.match(value):
            raise ValueError("Invalid email format")
        return value

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    first_name: str | None = None
    last_name: str | None = None
    role: str
    created_at: datetime | str


class UserSummary(BaseModel):
    id: str
    email: str
    name: str
    first_name: str | None = None
    last_name: str | None = None
    role: str


class LoginInput(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary


@users_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegisterInput) -> dict:
    email_clean = payload.email.strip()
    name_clean = payload.name.strip()
    pwd_hash = hash_password(payload.password)
    user_id = uuid4()
    first_name, last_name = split_name(name_clean)

    try:
        with get_connection() as conn:
            # Check duplicate email
            existing = conn.execute(
                "SELECT id FROM users WHERE LOWER(email) = LOWER(%s)",
                (email_clean,),
            ).fetchone()
            if existing:
                raise ApiError(
                    409,
                    "EMAIL_ALREADY_EXISTS",
                    "A user with this email address already exists",
                )

            phase = get_migration_phase(conn)

            if phase == "contract":
                # Phase 5: Column 'name' is dropped, write only first_name and last_name
                row = conn.execute(
                    """
                    INSERT INTO users (id, email, first_name, last_name, password_hash, role, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, now())
                    RETURNING id, email, first_name, last_name, role, created_at
                    """,
                    (user_id, email_clean, first_name, last_name, pwd_hash, payload.role),
                ).fetchone()
            elif phase in ("dual_write", "backfill", "switch_read"):
                # Phase 2, 3, 4: Dual-write to both old and new columns
                row = conn.execute(
                    """
                    INSERT INTO users (id, email, name, first_name, last_name, password_hash, role, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                    RETURNING id, email, name, first_name, last_name, role, created_at
                    """,
                    (user_id, email_clean, name_clean, first_name, last_name, pwd_hash, payload.role),
                ).fetchone()
            else:
                # Phase 1: Expand - write to old column 'name' (trigger will populate first_name/last_name as safety net)
                row = conn.execute(
                    """
                    INSERT INTO users (id, email, name, password_hash, role, created_at)
                    VALUES (%s, %s, %s, %s, %s, now())
                    RETURNING id, email, name, role, created_at
                    """,
                    (user_id, email_clean, name_clean, pwd_hash, payload.role),
                ).fetchone()

            conn.commit()

            computed_name = row.get("name") or f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
            return {
                "id": str(row["id"]),
                "email": row["email"],
                "name": computed_name,
                "first_name": row.get("first_name") or first_name,
                "last_name": row.get("last_name") or last_name,
                "role": row["role"],
                "created_at": row["created_at"].isoformat()
                if isinstance(row["created_at"], datetime)
                else str(row["created_at"]),
            }
    except UniqueViolation as error:
        raise ApiError(
            409,
            "EMAIL_ALREADY_EXISTS",
            "A user with this email address already exists",
        ) from error


@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(payload: LoginInput) -> dict:
    email_clean = payload.email.strip()

    with get_connection() as conn:
        phase = get_migration_phase(conn)

        if phase == "contract":
            row = conn.execute(
                """
                SELECT id, email, first_name, last_name, password_hash, role
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                """,
                (email_clean,),
            ).fetchone()
        elif phase >= "switch_read":
            row = conn.execute(
                """
                SELECT id, email, first_name, last_name, password_hash, role
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                """,
                (email_clean,),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT id, email, name, password_hash, role
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                """,
                (email_clean,),
            ).fetchone()

    if not row or not verify_password(payload.password, row["password_hash"]):
        raise ApiError(401, "INVALID_CREDENTIALS", "Invalid email or password")

    computed_name = row.get("name") or f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
    token = create_access_token(user_id=row["id"], role=row["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(row["id"]),
            "email": row["email"],
            "name": computed_name,
            "first_name": row.get("first_name"),
            "last_name": row.get("last_name"),
            "role": row["role"],
        },
    }


@users_router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user_by_id(
    user_id: UUID,
    claims: dict = Depends(current_user_claims),
) -> dict:
    requester_id = claims.get("user_id")
    requester_role = claims.get("role")

    if requester_id != user_id and requester_role != "admin":
        raise ApiError(403, "FORBIDDEN", "Access denied")

    with get_connection() as conn:
        phase = get_migration_phase(conn)

        if phase in ("contract", "switch_read"):
            row = conn.execute(
                """
                SELECT id, email, first_name, last_name, role, created_at
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT id, email, name, role, created_at
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            ).fetchone()

    if not row:
        raise ApiError(404, "USER_NOT_FOUND", "User not found")

    computed_name = row.get("name") or f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "name": computed_name,
        "first_name": row.get("first_name"),
        "last_name": row.get("last_name"),
        "role": row["role"],
        "created_at": row["created_at"].isoformat()
        if isinstance(row["created_at"], datetime)
        else str(row["created_at"]),
    }
