from dataclasses import dataclass
from typing import Annotated, Callable
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.core.security import decode_bearer_token, require_scope_org
from app.database import get_session
from app.models.user import User
from app.models.enums import Role

bearer = HTTPBearer(auto_error=False)
ROLE_ORDER = {Role.viewer: 0, Role.editor: 1, Role.approver: 2, Role.admin: 3}

@dataclass
class CurrentUser:
    id: str
    org_id: str
    email: str
    name: str
    role: Role
    claims: dict

async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentUser:
    settings = get_settings()
    if settings.auth_disabled_for_local_dev and settings.environment == 'local':
        return CurrentUser(id='00000000-0000-0000-0000-000000000001', org_id='00000000-0000-0000-0000-000000000001', email='dev@example.com', name='Local Dev', role=Role.admin, claims={})
    token = credentials.credentials if credentials else request.query_params.get('token')
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing bearer token')
    claims = await decode_bearer_token(token)
    org_id = require_scope_org(claims)
    auth_id = claims.get('sub')
    email = claims.get('email', '')
    role = Role(claims.get('role') or claims.get('https://agentic/role') or Role.viewer)
    user = await session.scalar(select(User).where(User.org_id == org_id, User.auth_provider_id == auth_id))
    if user:
        return CurrentUser(id=str(user.id), org_id=str(user.org_id), email=user.email, name=user.name, role=user.role, claims=claims)
    return CurrentUser(id=claims.get('user_id', '00000000-0000-0000-0000-000000000000'), org_id=org_id, email=email, name=claims.get('name', email), role=role, claims=claims)


def require_role(*allowed_roles: Role):
    async def _require_role(
        user: CurrentUser = Depends(get_current_user),
    ):
        user_role = user.role

        # Support both Enum values and plain string roles
        if isinstance(user_role, str):
            user_role_value = user_role
        else:
            user_role_value = user_role.value

        allowed_role_values = [
            role.value if not isinstance(role, str) else role
            for role in allowed_roles
        ]

        # Admin can access any role-protected endpoint
        if user_role_value == Role.admin.value:
            return user

        if user_role_value not in allowed_role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return user

    return _require_role