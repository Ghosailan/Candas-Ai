from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def retrieve_similar_campaigns(session: AsyncSession, org_id: str, query: str, limit: int = 5) -> str:
    # Production implementation should embed query and use pgvector distance.
    # Local-safe fallback returns recent content, still enforcing org-level isolation.
    result = await session.execute(
        text('SELECT content FROM campaign_embeddings WHERE org_id = :org_id ORDER BY created_at DESC LIMIT :limit'),
        {'org_id': org_id, 'limit': limit},
    )
    return '\n---\n'.join(row[0] for row in result.fetchall())

async def write_campaign_memory(session: AsyncSession, org_id: str, campaign_id: str, content: str, embedding: str | None = None) -> None:
    await session.execute(
        text('INSERT INTO campaign_embeddings (org_id, campaign_id, content, embedding) VALUES (:org_id, :campaign_id, :content, :embedding)'),
        {'org_id': org_id, 'campaign_id': campaign_id, 'content': content, 'embedding': embedding},
    )
