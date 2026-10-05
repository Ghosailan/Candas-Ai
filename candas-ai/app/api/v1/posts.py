from typing import Annotated

from flask import request, session
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import CurrentUser, get_current_user, require_role
from app.database import get_session
from app.models.enums import PostStatus, Role
from app.models.post import Post
from app.schemas.common import success
from app.schemas.post import PostResponse, PostUpdateRequest, SchedulePostRequest
from app.services.publishing_service import get_schedule_log, serialize_post, upsert_schedule_log
from app.workers.campaign_tasks import publish_post_task

router = APIRouter(prefix='/posts', tags=['posts'])

@router.post('/{post_id}/schedule', response_model=dict, status_code=202)
async def schedule_post(
    post_id: str,
    payload: SchedulePostRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(require_role(Role.editor))],
):
    post = await session.scalar(
        select(Post).where(
            Post.id == post_id,
            Post.org_id == user.org_id,
        )
    )

    if not post:
        raise HTTPException(status_code=404, detail='Post not found')

    if post.status == PostStatus.published:
        raise HTTPException(status_code=400, detail='Published posts cannot be rescheduled.')

    log = await upsert_schedule_log(session, post, payload.publish_at)

    # Build response before commit to avoid async SQLAlchemy expired-object access.
    response_data = {
        'post_id': str(post.id),
        'status': post.status.value,
        'publish_at': log.scheduled_at.isoformat() if log.scheduled_at else None,
        'publishing_status': log.status.value,
    }

    await session.commit()

    return success(response_data, request.state.trace_id)

@router.post('/{post_id}/publish', response_model=dict, status_code=202)
async def publish_post(post_id: str, request: Request, user: Annotated[CurrentUser, Depends(require_role(Role.editor))]):
    publish_post_task.delay(post_id, 'now', request.state.trace_id)
    return success({'post_id': post_id, 'status': 'queued'}, request.state.trace_id)


@router.patch('/{post_id}', response_model=dict)
async def update_post(
    post_id: str,
    payload: PostUpdateRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(require_role(Role.editor))],
):
    post = await session.scalar(select(Post).where(Post.id == post_id, Post.org_id == user.org_id))
    if not post:
        raise HTTPException(status_code=404, detail='Post not found')
    if post.status == PostStatus.published and any(
        value is not None for key, value in payload.model_dump(exclude_unset=True).items() if key != 'image_url'
    ):
        raise HTTPException(status_code=400, detail='Published posts cannot be edited.')
    updates = payload.model_dump(exclude_unset=True)
    if 'copy' in updates and updates['copy'] is not None:
        post.copy = updates['copy']
    if 'image_prompt' in updates:
        post.image_prompt = updates['image_prompt']
    if 'image_url' in updates:
        post.image_url = updates['image_url']
    log = await get_schedule_log(session, post.id)
    if 'publish_at' in updates and updates['publish_at'] is not None:
        if post.status == PostStatus.published:
            raise HTTPException(status_code=400, detail='Published posts cannot be rescheduled.')
        log = await upsert_schedule_log(session, post, updates['publish_at'])
    response_data = serialize_post(post, log)

    await session.commit()

    return success(response_data, request.state.trace_id)

@router.get('/scheduled', response_model=dict)
async def scheduled_posts(request: Request, user: Annotated[CurrentUser, Depends(get_current_user)]):
    return success([], request.state.trace_id)


@router.get('', response_model=dict)
async def list_posts(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
    campaign_id: str | None = None,
):
    query = select(Post).where(Post.org_id == user.org_id).options(selectinload(Post.campaign)).order_by(Post.created_at.desc())
    if campaign_id:
        query = query.where(Post.campaign_id == campaign_id)
    rows = (await session.scalars(query)).all()
    data = []
    for row in rows:
        log = await get_schedule_log(session, row.id)
        base = PostResponse.model_validate(row).model_dump(mode='json')
        base.update(
            {
                'publish_at': log.scheduled_at.isoformat() if log and log.scheduled_at else None,
                'publishing_status': log.status.value if log else None,
            }
        )
        data.append(base)
    return success(data, request.state.trace_id)
