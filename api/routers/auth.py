from fastapi import APIRouter, HTTPException, status
from api.schemas import TokenRequest, TokenResponse
from api.auth import create_access_token

router = APIRouter(prefix="/v1/auth", tags=["Authentication & Tokens"])


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Generate access token for tenant user or auditor",
)
def issue_token(req: TokenRequest):
    """
    Issues a JWT bearer token for testing and local integration.
    """
    token = create_access_token(
        tenant_id=req.tenant_id,
        actor=req.actor,
        role=req.role,
    )
    return TokenResponse(access_token=token, token_type="bearer")
