from fastapi import Request
from fastapi.responses import JSONResponse
from structlog import get_logger

log = get_logger()


class AppError(Exception):
    status_code = 400
    error_code = 'application_error'

    def __init__(self, message: str, *, detail: dict | None = None):
        self.message = message
        self.detail = detail or {}
        super().__init__(message)


class PlatformPublishError(AppError):
    status_code = 502
    error_code = 'platform_publish_error'


class ApprovalRequired(AppError):
    status_code = 409
    error_code = 'approval_required'


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    trace_id = getattr(request.state, 'trace_id', None)
    log.warning('application_error', trace_id=trace_id, error=exc.error_code, detail=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={'status': 'error', 'data': {'error': exc.error_code, 'message': exc.message, 'detail': exc.detail}, 'meta': {'trace_id': trace_id}},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    trace_id = getattr(request.state, 'trace_id', None)
    log.exception('unhandled_exception', trace_id=trace_id, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={'error': 'internal_server_error', 'trace_id': trace_id},
    )
