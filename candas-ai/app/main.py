import uuid
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.extension import _rate_limit_exceeded_handler
import structlog
from app.api.v1 import api_router, v2_router
from app.config import get_settings
from app.core.exceptions import AppError, app_error_handler, unhandled_exception_handler
from app.core.logging import configure_logging
from app.core.telemetry import setup_telemetry
from app.database import engine

configure_logging()
log = structlog.get_logger()
settings = get_settings()


def user_or_ip(request: Request) -> str:
    auth = request.headers.get('authorization', '')
    return auth[-16:] if auth else get_remote_address(request)

limiter = Limiter(key_func=user_or_ip, default_limits=[settings.rate_limit_authenticated], storage_uri=settings.redis_url)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.api_version, docs_url='/docs', redoc_url='/redoc')
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(set([*settings.cors_allowed_origins, 'http://localhost:5173'])),
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.middleware('http')
    async def trace_middleware(request: Request, call_next):
        trace_id = request.headers.get('X-Trace-ID') or str(uuid.uuid4())
        request.state.trace_id = trace_id
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        response = await call_next(request)
        response.headers['X-Trace-ID'] = trace_id
        return response

    @app.get('/health', tags=['system'])
    async def health():
        return {'status': 'ok', 'version': settings.api_version}

    @app.get('/v1/health', tags=['system'])
    async def v1_health():
        return {
            'status': 'ok',
            'version': settings.api_version,
            'environment': settings.environment,
            'database': 'configured',
            'redis': 'configured',
            'platform_mock_mode': settings.platform_mock_mode,
            'ollama': {
                'base_url': settings.ollama_base_url,
                'primary_model': settings.ollama_primary_model,
                'fallback_model': settings.ollama_fallback_model,
            },
        }

    app.include_router(api_router)
    app.include_router(v2_router)

    dist_dir = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
    assets_dir = dist_dir / 'assets'
    index_file = dist_dir / 'index.html'
    if assets_dir.exists():
        app.mount('/app/assets', StaticFiles(directory=assets_dir), name='app-assets')

    @app.get('/app', include_in_schema=False)
    @app.get('/app/{path:path}', include_in_schema=False)
    async def serve_frontend(path: str = ''):
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse(
            {
                'status': 'frontend_not_built',
                'message': 'Frontend assets are not built yet. Use the Vite dev server on http://localhost:5173/app or run npm run build in frontend/.',
            },
            status_code=503,
        )

    setup_telemetry(app, engine)
    return app

app = create_app()
