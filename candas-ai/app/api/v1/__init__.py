from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.posts import router as posts_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.users import router as users_router

api_router = APIRouter(prefix='/v1')
api_router.include_router(auth_router)
api_router.include_router(campaigns_router)
api_router.include_router(posts_router)
api_router.include_router(approvals_router)
api_router.include_router(analytics_router)
api_router.include_router(webhooks_router)
api_router.include_router(users_router)

v2_router = APIRouter(prefix='/v2')
@v2_router.get('/health', tags=['system'])
async def v2_health_stub():
    return {'status': 'reserved'}
