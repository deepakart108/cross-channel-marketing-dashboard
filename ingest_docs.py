"""
ingest_docs.py — Chunk platform guidance markdown files and upload embeddings to Pinecone.

Usage:
    1. Put platform guidance .md files in ./docs/platform_guidance/.
    2. Set PINECONE_API_KEY in .env.
    3. Run: python3 ingest_docs.py
"""

import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from fastembed import TextEmbedding

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME       = "marketing-dashboard-docs"
DOCS_DIR         = "./docs/platform_guidance"
EMBEDDING_MODEL  = "BAAI/bge-small-en-v1.5"  # 384-dim, ONNX-based (no PyTorch needed)
EMBEDDING_DIM    = 384
BATCH_SIZE       = 100
MAX_CHUNK_CHARS  = 1200   # approx 250 tokens — safe for Pinecone metadata
OVERLAP_WORDS    = 15     # words carried over between split sub-chunks

# filename -> platform key, used to filter retrieval to the flagged platform/channel
FILENAME_TO_PLATFORM = {
    "meta_ads.md": "meta",
    "google_ads_search.md": "google_search",
    "tiktok_ads.md": "tiktok",
    "pinterest_ads.md": "pinterest",
    "snapchat_ads.md": "snapchat",
    "mailchimp_email.md": "mailchimp",
    "programmatic_viewability.md": "programmatic",
}
# ──────────────────────────────────────────────────────────────────────────────


def chunk_markdown(text: str, filename: str) -> list[dict]:
    """
    Split a markdown file into chunks on any header line (# / ## / ### / ####).
    Each chunk carries the header as its section title.
    Long sections are further split with a small word overlap.
    """
    chunks = []
    platform = FILENAME_TO_PLATFORM.get(filename, "")

    raw_sections = re.split(r"(?=\n#{1,4} )", "\n" + text)

    for section in raw_sections:
        section = section.strip()
        if not section:
            continue

        header_match = re.match(r"^(#{1,4})\s+(.+)", section)
        section_title = header_match.group(2).strip() if header_match else filename

        if len(section) < 60:
            continue

        if len(section) <= MAX_CHUNK_CHARS:
            chunks.append({
                "text": section,
                "source_file": filename,
                "section": section_title,
                "platform": platform,
            })
        else:
            words = section.split()
            sub_idx = 0
            current: list[str] = []
            current_len = 0

            for word in words:
                current.append(word)
                current_len += len(word) + 1

                if current_len >= MAX_CHUNK_CHARS:
                    sub_text = " ".join(current)
                    chunks.append({
                        "text": sub_text,
                        "source_file": filename,
                        "section": f"{section_title} (part {sub_idx + 1})",
                        "platform": platform,
                    })
                    sub_idx += 1
                    current = current[-OVERLAP_WORDS:]
                    current_len = sum(len(w) + 1 for w in current)

            if current:
                sub_text = " ".join(current)
                if len(sub_text) >= 60:
                    chunks.append({
                        "text": sub_text,
                        "source_file": filename,
                        "section": f"{section_title} (part {sub_idx + 1})" if sub_idx else section_title,
                        "platform": platform,
                    })

    return chunks


def main():
    print("Connecting to Pinecone…")
    pc = Pinecone(api_key=PINECONE_API_KEY)

    existing = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME not in existing:
        print(f"Creating index '{INDEX_NAME}' (this takes ~30 s)…")
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pc.describe_index(INDEX_NAME).status["ready"]:
            print("  Waiting for index to be ready…")
            time.sleep(5)
        print("Index ready.")
    else:
        print(f"Index '{INDEX_NAME}' already exists — upserting into it.")

    index = pc.Index(INDEX_NAME)

    print(f"\nLoading embedding model '{EMBEDDING_MODEL}'…")
    model = TextEmbedding(EMBEDDING_MODEL)

    docs_path = Path(DOCS_DIR)
    md_files = sorted(docs_path.glob("*.md"))

    if not md_files:
        print(f"\nERROR: No .md files found in '{DOCS_DIR}'.")
        return

    print(f"\nFound {len(md_files)} markdown file(s).")
    all_chunks: list[dict] = []

    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        chunks = chunk_markdown(text, md_file.name)
        all_chunks.extend(chunks)
        print(f"  {md_file.name:40s}  →  {len(chunks):3d} chunk(s)")

    print(f"\nTotal chunks to upload: {len(all_chunks)}")

    print("\nGenerating embeddings and uploading to Pinecone…")
    total_batches = (len(all_chunks) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num, start in enumerate(range(0, len(all_chunks), BATCH_SIZE), 1):
        batch = all_chunks[start : start + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        embeds = [e.tolist() for e in model.embed(texts)]

        vectors = [
            {
                "id": f"chunk_{start + i}",
                "values": embedding,
                "metadata": {
                    "text": chunk["text"],
                    "source_file": chunk["source_file"],
                    "section": chunk["section"],
                    "platform": chunk["platform"],
                },
            }
            for i, (chunk, embedding) in enumerate(zip(batch, embeds))
        ]

        index.upsert(vectors=vectors)
        print(f"  Batch {batch_num}/{total_batches} uploaded ({len(vectors)} vectors)")

    print(f"\nDone! {len(all_chunks)} chunks are live in Pinecone index '{INDEX_NAME}'.")


if __name__ == "__main__":
    main()
