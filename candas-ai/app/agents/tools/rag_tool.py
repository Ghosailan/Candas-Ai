from langchain_core.tools import tool

@tool('rag_tool')
def rag_tool(query: str, top_k: int = 5) -> str:
    """Retrieve related brand/campaign knowledge. The async DB-backed version is used inside nodes."""
    return f'RAG query prepared: {query[:200]} top_k={top_k}'
