from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')

class Meta(BaseModel):
    trace_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = '1.0'

class Envelope(BaseModel, Generic[T]):
    status: str
    data: T | None = None
    meta: Meta


def success(data: Any, trace_id: str | None = None) -> dict[str, Any]:
    return {'status': 'success', 'data': data, 'meta': Meta(trace_id=trace_id).model_dump(mode='json')}
