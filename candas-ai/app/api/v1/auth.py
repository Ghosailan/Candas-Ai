from datetime import datetime, timedelta, timezone
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.database import get_session
from app.models import Organisation, User
from app.models.enums import Plan
from app.schemas.auth import LocalTokenRequest, LocalTokenResponse
from app.schemas.common import success

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/local-token', response_model=dict)
async def issue_local_token(
    payload: LocalTokenRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    settings = get_settings()
    if settings.auth_provider != 'local':
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Local auth is disabled')

    org = await session.scalar(select(Organisation).where(Organisation.name == payload.org_name))
    if not org:
        org = Organisation(id=uuid.uuid4(), name=payload.org_name, plan=Plan.free)
        session.add(org)
        await session.flush()

    auth_provider_id = payload.email.lower()
    user = await session.scalar(
        select(User).where(User.org_id == org.id, User.auth_provider_id == auth_provider_id)
    )
    if not user:
        user = User(
            id=uuid.uuid4(),
            org_id=org.id,
            email=payload.email,
            name=payload.name,
            role=payload.role,
            auth_provider_id=auth_provider_id,
        )
        session.add(user)
    else:
        user.email = payload.email
        user.name = payload.name
        user.role = payload.role

    await session.commit()
    await session.refresh(user)

    now = datetime.now(timezone.utc)
    claims = {
        'sub': user.auth_provider_id,
        'user_id': str(user.id),
        'org_id': str(user.org_id),
        'email': user.email,
        'name': user.name,
        'role': user.role.value,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(hours=12)).timestamp()),
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    data = LocalTokenResponse(
        access_token=token,
        user={
            'id': str(user.id),
            'org_id': str(user.org_id),
            'email': user.email,
            'name': user.name,
            'role': user.role.value,
        },
    )
    return success(data.model_dump(mode='json'), request.state.trace_id)
