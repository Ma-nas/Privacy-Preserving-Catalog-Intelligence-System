import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from config import settings

security_bearer = HTTPBearer(auto_error=False)


class Principal(BaseModel):
    tenant_id: Optional[str] = None
    actor: str
    role: str = "tenant_user"  # 'tenant_user' | 'tenant_admin' | 'auditor' | 'platform_ops'


def create_access_token(
    tenant_id: Optional[str],
    actor: str,
    role: str = "tenant_user",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generates a signed JWT access token for authentication."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": actor,
        "role": role,
        "exp": expire,
    }
    if tenant_id:
        to_encode["tenant_id"] = str(tenant_id)

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def get_current_principal(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> Principal:
    """
    Decodes and validates the JWT bearer token.
    Extracts the authenticated principal (actor, role, and tenant_id).
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        actor: str = payload.get("sub")
        role: str = payload.get("role", "tenant_user")
        tenant_id: Optional[str] = payload.get("tenant_id")

        if actor is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject identifier",
            )

        return Principal(tenant_id=tenant_id, actor=actor, role=role)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_tenant_access(
    tenant_id: str,
    principal: Principal = Depends(get_current_principal),
) -> str:
    """
    Non-negotiable rule §6.2:
    tenant_id from the path is cross-checked against the authenticated principal's tenant.
    Never trust path or body param for authorization.
    """
    if principal.role == "platform_ops":
        # Platform ops can perform diagnostic routing for specified tenant
        return tenant_id

    if not principal.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Principal has no assigned tenant identity",
        )

    try:
        path_uuid = uuid.UUID(str(tenant_id))
        principal_uuid = uuid.UUID(str(principal.tenant_id))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id format. Must be a valid UUID.",
        )

    if path_uuid != principal_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access forbidden: Authenticated tenant does not match target resource path.",
        )

    return str(path_uuid)


def require_auditor(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """Restricts endpoint to auditor or compliance review role."""
    if principal.role not in ("auditor", "compliance_reviewer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Auditor privileges required.",
        )
    return principal
