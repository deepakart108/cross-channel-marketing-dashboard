# Cross-Channel Marketing Performance Dashboard

Ingests exported performance data from multiple marketing channels (paid social, paid search,
programmatic, email), normalizes it into a unified schema, runs it through a domain-expert
rules engine, and uses Claude (grounded via RAG on official platform documentation) to generate
prioritized, cross-channel insights and recommended next steps — automating the manual
weekly/quarterly reporting process used at marketing agencies.

**Architecture:** ingest → normalize → rules engine → AI-enrich (RAG-grounded) → dashboard.

## Channels in scope
Meta (Facebook/Instagram) Ads, Google Ads (Search), TikTok Ads, Pinterest Ads, Snapchat Ads,
Programmatic/DSP (generic schema), Mailchimp (email).

## Stack
- Backend: Python / Flask
- AI: Claude API (Sonnet)
- Vector store: Pinecone (RAG over platform documentation)
- Frontend: dark-theme dashboard
- Hosting: Railway

## Setup
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY, PINECONE_API_KEY
python3 app.py          # http://localhost:5000
```

## Project layout
```
app.py              Flask dashboard
rules.py             Domain-expert rules engine
rag.py                RAG retrieval + Claude insight generation
ingest/
  schema.py           Unified schema definition
  normalize.py        Per-channel export normalizers
data/sample_exports/  Sample/demo CSV & Excel exports
```

## Status
Scaffolding only — ingestion normalizers, rules, and RAG pipeline are stubbed pending
implementation. See `marketing-dashboard-build-spec.md` for the full build spec.

## Live link
TBD
