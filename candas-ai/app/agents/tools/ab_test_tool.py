import random
from langchain_core.tools import tool

@tool('ab_test_tool')
def ab_test_tool(post_a: dict, post_b: dict, split_ratio: float = 0.5) -> dict:
    """Select A/B variant assignment based on a split ratio."""
    chosen = 'A' if random.random() < split_ratio else 'B'
    return {'variant': chosen, 'post': post_a if chosen == 'A' else post_b}
