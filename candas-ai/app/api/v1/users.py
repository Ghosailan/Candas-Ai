from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import CurrentUser, require_role
from app.database import get_session
from app.models.enums import Role
from app.schemas.common import success
from app.services.auth import delete_user_data

router = APIRouter(prefix='/users', tags=['users'])

@router.delete('/{user_id}/data', response_model=dict)
async def gdpr_delete(user_id: UUID, request: Request, session: Annotated[AsyncSession, Depends(get_session)], user: Annotated[CurrentUser, Depends(require_role(Role.admin))]):
    await delete_user_data(session, user.org_id, user_id)
    return success({'user_id': str(user_id), 'deleted': True}, request.state.trace_id)
