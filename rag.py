"""RAG layer: ground rule-engine flags in official platform documentation.

Pipeline: chunk platform docs -> Pinecone embeds + stores them (integrated
inference — no local embedding model) -> at insight-generation time, retrieve
chunks relevant to a Flag -> Claude synthesizes the flag + retrieved doc
context into a narrative insight card.
"""

import os

from anthropic import Anthropic
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

PINECONE_INDEX_NAME = "marketing-dashboard-docs"
PINECONE_NAMESPACE = "platform-guidance"
CLAUDE_MODEL = "claude-sonnet-5"

# Flags whose channel is "programmatic" carry the DSP name (e.g. "Generic DSP") as
# their platform, not a fixed key — route those to the programmatic guidance doc
# by channel instead of by platform string.
CHANNEL_TO_DOC_PLATFORM = {"programmatic": "programmatic"}

# Explicit timeout on the Anthropic client: a hang here would otherwise block
# app.py's background build thread indefinitely — each flag's work is
# wrapped in a try/except there, but only a raised error (not an unbounded
# wait) gets caught and turned into a fallback insight card.
anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"), timeout=30.0)
pinecone_client = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
# Pinecone's integrated embedding (index created via create_index_for_model in
# ingest_docs.py) means Pinecone embeds both the stored chunks and this query
# server-side — no local embedding model (fastembed/onnxruntime) runs in this
# process. That dependency alone was pushing the deployed app's memory right
# up against Render's free-tier 512MB cap and causing repeated OOM restarts.
_index = pinecone_client.Index(PINECONE_INDEX_NAME)


def retrieve_context(flag, top_k: int = 5):
    """Query Pinecone for doc chunks relevant to a rules.Flag's platform."""
    doc_platform = CHANNEL_TO_DOC_PLATFORM.get(flag.channel, flag.platform)
    query = f"{flag.rule_id} {flag.what_happened}"

    results = _index.search(
        namespace=PINECONE_NAMESPACE,
        inputs={"text": query},
        top_k=top_k,
        filter={"platform": {"$eq": doc_platform}},
        fields=["chunk_text", "source_file", "section"],
        timeout=30.0,
    )
    return [
        {"text": hit.fields.get("chunk_text"), "source_file": hit.fields.get("source_file"), "section": hit.fields.get("section")}
        for hit in results.result.hits
    ]


def generate_insight(flag, context_chunks):
    """Ask Claude to turn a Flag + retrieved doc context into an insight card:
    why it matters, recommended next step, and source grounding. Claude only
    narrates the flag the rules engine already produced — it does not decide
    whether something is worth flagging.
    """
    context = "\n\n---\n\n".join(
        f"[Source: {c.get('source_file')} › {c.get('section')}]\n{c.get('text')}"
        for c in context_chunks
    ) or "(no matching platform guidance found)"

    user_message = f"""A domain-expert rules engine flagged the following, deterministically — do not \
second-guess or restate whether it's worth flagging, only explain it:

Rule: {flag.rule_id}
Platform: {flag.platform}
Campaign: {flag.campaign_name}
Period: {flag.period}
What happened: {flag.what_happened}

Official platform guidance excerpts (use ONLY these to ground your explanation — do not draw on \
general knowledge about the platform beyond what's here):

{context}

Using only the flag above and the guidance excerpts, provide:
- why_it_matters: the business impact, in 1-2 sentences, citing the guidance where relevant
- recommended_next_step: one specific, actionable step (not generic advice like "optimize your campaign")
- source_grounding: which excerpt(s) (by file/section) informed the recommendation, or "general marketing practice" if the excerpts didn't directly cover it
"""

    response = anthropic_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        thinking={"type": "disabled"},
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "why_it_matters": {"type": "string"},
                        "recommended_next_step": {"type": "string"},
                        "source_grounding": {"type": "string"},
                    },
                    "required": ["why_it_matters", "recommended_next_step", "source_grounding"],
                    "additionalProperties": False,
                },
            }
        },
        messages=[{"role": "user", "content": user_message}],
    )

    import json

    narration = json.loads(next(b.text for b in response.content if b.type == "text"))

    return {
        "rule_id": flag.rule_id,
        "channel": flag.channel,
        "platform": flag.platform,
        "campaign_name": flag.campaign_name,
        "period": flag.period,
        "materiality": flag.materiality,
        "what_happened": flag.what_happened,
        **narration,
    }
