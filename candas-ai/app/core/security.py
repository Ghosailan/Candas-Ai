import hmac
import hashlib
import time
from typing import Any
from uuid import UUID
import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, Request, status
from app.config import get_settings

_jwks_cache: dict[str, Any] = {'expires_at': 0, 'keys': None}


def verify_hmac_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    if not signature:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    supplied = signature.replace('sha256=', '')
    return hmac.compare_digest(expected, supplied)


async def _fetch_jwks(issuer_url: str) -> dict[str, Any]:
    now = time.time()
    if _jwks_cache['keys'] and _jwks_cache['expires_at'] > now:
        return _jwks_cache['keys']
    jwks_url = issuer_url.rstrip('/') + '/.well-known/jwks.json'
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
    _jwks_cache['keys'] = response.json()
    _jwks_cache['expires_at'] = now + 3600
    return _jwks_cache['keys']


async def decode_bearer_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    if settings.auth_provider == 'local' or settings.jwt_algorithm.startswith('HS'):
        try:
            return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid bearer token') from exc

    issuer = f'https://{settings.auth0_domain}/' if settings.auth_provider == 'auth0' else settings.keycloak_issuer
    audience = settings.auth0_audience if settings.auth_provider == 'auth0' else settings.keycloak_audience
    if not issuer:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Auth issuer is not configured')
    jwks = await _fetch_jwks(issuer)
    try:
        header = jwt.get_unverified_header(token)
        key = next(k for k in jwks['keys'] if k['kid'] == header['kid'])
        return jwt.decode(token, key, algorithms=[settings.jwt_algorithm], audience=audience, issuer=issuer)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid bearer token') from exc


def require_scope_org(claims: dict[str, Any]) -> str:
    org_id = claims.get('org_id') or claims.get('https://agentic/org_id')
    if not org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Missing org_id claim')
    return str(org_id)
