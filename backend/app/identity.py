import os
from uuid import UUID

import jwt
from fastapi import Header

from app.errors import ApiError


def current_user_claims(authorization: str = Header(default="")) -> dict:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiError(401, "UNAUTHENTICATED", "Bearer token required")
    try:
        claims = jwt.decode(
            token,
            os.environ["AUTH_SECRET"],
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
        claims["user_id"] = UUID(claims["sub"])
        return claims
    except (jwt.PyJWTError, ValueError, TypeError, KeyError) as error:
        raise ApiError(401, "UNAUTHENTICATED", "Invalid bearer token") from error


def current_user_id(authorization: str = Header(default="")) -> UUID:
    claims = current_user_claims(authorization)
    return claims["user_id"]


def current_customer_id(authorization: str = Header(default="")) -> UUID:
    claims = current_user_claims(authorization)
    if claims.get("role") != "customer":
        raise ApiError(403, "FORBIDDEN", "Customer access required")
    return claims["user_id"]
