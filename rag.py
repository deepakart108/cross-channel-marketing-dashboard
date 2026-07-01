"""RAG layer: ground rule-engine flags in official platform documentation.

Pipeline: chunk platform docs -> embed (fastembed) -> store in Pinecone ->
at insight-generation time, retrieve chunks relevant to a Flag -> Claude
synthesizes the flag + retrieved doc context into a narrative insight card.
"""

import os

from anthropic import Anthropic
from pinecone import Pinecone

PINECONE_INDEX_NAME = "marketing-dashboard-docs"

anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
pinecone_client = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))


def retrieve_context(flag, top_k: int = 5):
    """Query Pinecone for doc chunks relevant to a rules.Flag."""
    raise NotImplementedError


def generate_insight(flag, context_chunks):
    """Ask Claude to turn a Flag + retrieved doc context into an insight card:
    what happened, why it matters, recommended next step, source grounding.
    """
    raise NotImplementedError
