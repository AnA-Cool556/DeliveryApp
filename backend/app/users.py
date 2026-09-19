import os
import re
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from app.errors import ApiError
from app.identity import current_user_claims
from app.security import create_access_token, hash_password, verify_password

users_router = APIRouter(prefix="/api/v1/users", tags=["Users"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _connection() -> psycopg.Connection:
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    return psycopg.connect(url, row_factory=dict_row)


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
    role: str
    created_at: datetime | str


class UserSummary(BaseModel):
    id: str
    email: str
    name: str
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

    try:
        with _connection() as conn:
            # Explicit check for existing case-insensitive email
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

            row = conn.execute(
                """
                INSERT INTO users (id, email, name, password_hash, role, created_at)
                VALUES (%s, %s, %s, %s, %s, now())
                RETURNING id, email, name, role, created_at
                """,
                (user_id, email_clean, name_clean, pwd_hash, payload.role),
            ).fetchone()
            conn.commit()

            return {
                "id": str(row["id"]),
                "email": row["email"],
                "name": row["name"],
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

    with _connection() as conn:
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

    token = create_access_token(user_id=row["id"], role=row["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(row["id"]),
            "email": row["email"],
            "name": row["name"],
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

    with _connection() as conn:
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

    return {
        "id": str(row["id"]),
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
        "created_at": row["created_at"].isoformat()
        if isinstance(row["created_at"], datetime)
        else str(row["created_at"]),
    }

