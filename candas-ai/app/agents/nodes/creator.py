from sqlalchemy import delete
from app.database import get_sessionmaker
from app.models.enums import Platform, PostStatus
from app.models.post import Post
from app.agents.tools.llm_tool import ollama_generate, extract_json
from app.agents.tools.brand_compliance_tool import check_brand_compliance
from app.agents.tools.media_gen_tool import generate_image
from app.core.telemetry import agent_span
from app.services.event_stream import publish_event
from app.services.moderation_service import moderate_text

CHAR_LIMITS = {'twitter': 280, 'linkedin': 3000, 'instagram': 2200, 'facebook': 63206, 'tiktok': 2200, 'youtube': 5000}
SYSTEM = 'You are a platform-native social media copywriter. Return valid JSON: {"posts":[{"platform":"...","copy":"...","image_prompt":"..."}]}. Respect platform character limits and brand guidelines. No markdown.'

async def creator_node(state):
    campaign_id = state['campaign_id']; trace_id = state.get('trace_id')
    await publish_event(campaign_id, 'node_started', 'creator', trace_id=trace_id)
    with agent_span('creator'):
        feedback = state.get('reviewer_feedback') or state.get('reflection_feedback') or ''
        prompt = f"Reviewer/reflection feedback to address first: {feedback}\nBrief: {state['brief']}\nPlatforms: {state['platforms']}\nGoals: {state.get('goals')}\nAudience: {state.get('target_audience')}\nBrand guidelines: {state.get('brand_guidelines')}\nResearch: {state.get('research_context')}"
        try:
            data = extract_json(await ollama_generate(SYSTEM, prompt, max_tokens=2500))
            posts = data.get('posts', [])
        except Exception:
            posts = [{'platform': p, 'copy': f"Discover our new campaign: {state['brief'][:160]}\nLearn more today.", 'image_prompt': f"Professional marketing image for: {state['brief'][:200]}"} for p in state['platforms']]
        drafts = []
        for p in posts:
            platform = p.get('platform')
            copy = (p.get('copy') or '')[:CHAR_LIMITS.get(platform, 2200)]
            moderation = await moderate_text(copy)
            flags = check_brand_compliance(copy)
            if moderation.flagged:
                flags['compliant'] = False
                flags.setdefault('violations', []).append('moderation_flagged:' + ','.join(moderation.categories))
            image_prompt = p.get('image_prompt') or f'Marketing visual for {state["brief"]}'
            image_url = await generate_image(image_prompt, platform)
            drafts.append({'platform': platform, 'copy': copy, 'image_prompt': image_prompt, 'image_url': image_url, 'compliance_flags': flags})
        async with get_sessionmaker()() as session:
            await session.execute(delete(Post).where(Post.campaign_id == state['campaign_id']))
            persisted = []
            for draft in drafts:
                post = Post(
                    org_id=state['org_id'],
                    campaign_id=state['campaign_id'],
                    platform=Platform(draft['platform']),
                    copy=draft['copy'],
                    image_prompt=draft['image_prompt'],
                    image_url=draft['image_url'],
                    status=PostStatus.draft,
                    compliance_flags=draft['compliance_flags'],
                )
                session.add(post)
                persisted.append((post, draft))
            await session.flush()
            for post, draft in persisted:
                draft['id'] = str(post.id)
            await session.commit()
        out = {'post_drafts': drafts}
    await publish_event(campaign_id, 'node_completed', 'creator', {'draft_count': len(drafts)}, trace_id=trace_id)
    return out
