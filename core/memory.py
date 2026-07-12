import chromadb
import hashlib
import json
import os

print("Initializing ChromaDB Memory...")
chroma_client = chromadb.PersistentClient("./chromadb")
collection = chroma_client.get_or_create_collection("news-events")


def dump_to_json(data: list | dict, filepath: str):
    """Saves pure JSON dumps to the hard drive for debugging and safety."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"📁 Data successfully dumped to: {filepath}")


def store_event(event: dict, cluster: list[dict] = None, collection=collection):
    """
    Writes the merged EVENT into ChromaDB. If `cluster` (the raw articles
    that built this event) is passed in, also stores each article
    individually via store_articles() — that's what makes "show me your
    sources" a real database lookup instead of trusting a text marker.
    """
    if "combined_summary" not in event or not event.get("embedding"):
        print("⚠️ Warning: Event missing summary or embedding. Skipping.")
        return

    # Hash title + date, not title alone — two outlets can run the exact
    # same headline on different days, and a title-only hash would let
    # one day's event silently overwrite another's in the database.
    title = event.get("primary_headline", "Untitled")
    date = event.get("event_date", "Unknown Date")
    event_id = hashlib.md5(f"{title}-{date}".encode()).hexdigest()

    metadata = {
        "title": title,
        "date": date,
        "sources": json.dumps(event.get("source_links", [])),
        "entities": json.dumps(event.get("entities", [])),
        "cluster_id": event.get("cluster_id", event_id),
        "type": "event"  # lets you filter event-level vs article-level rows later
    }

    try:
        collection.upsert(
            ids=[event_id],
            documents=[event["combined_summary"]],
            embeddings=[event["embedding"]],
            metadatas=[metadata]
        )
        print(f"🧠 Saved event: {title}")
    except Exception as e:
        print(f"❌ Error saving event to ChromaDB: {e}")
        return

    if cluster:
        store_articles(cluster, collection=collection)


def store_articles(cluster: list[dict], collection=collection):
    """
    Stores every raw article in a cluster as its own ChromaDB entry,
    tagged with cluster_id. One batched upsert call for the whole
    cluster — not a loop — since the disk round-trip is the expensive
    part, and the embeddings are already computed (free to reuse).
    """
    ids, documents, embeddings, metadatas = [], [], [], []

    for article in cluster:
        if not article.get("embedding") or not article.get("link"):
            continue  # nothing to cite without a real URL

        # Hash on the URL, not the title — an article has exactly one
        # canonical link, so this id is naturally stable across re-runs.
        article_id = hashlib.md5(article["link"].encode()).hexdigest()

        ids.append(article_id)
        documents.append(f"{article.get('title', '')} {article.get('summary', '')}")
        embeddings.append(article["embedding"])
        metadatas.append({
            "title": article.get("title", "No Title"),
            "source": article.get("source", article.get("_source", "Unknown")),
            "url": article["link"],
            "cluster_id": article.get("cluster_id", "Unassigned"),
            "type": "article"
        })

    if not ids:
        return

    try:
        collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        print(f"📎 Saved {len(ids)} source articles for traceability.")
    except Exception as e:
        print(f"❌ Error saving articles to ChromaDB: {e}")


def query_memory(user_question: str, embedding_model, collection=collection):
    """Retrieves historical context based on the user's question (RAG read path)."""
    print(f"🔎 Searching memory for: '{user_question}'...")

    query_vector = embedding_model.encode(user_question).tolist()

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=5
    )

    if not results["documents"] or not results["documents"][0]:
        return "No relevant historical context found.", []

    retrieved_texts = results["documents"][0]
    retrieved_metadatas = results["metadatas"][0]
    combined_context = "\n\n---\n\n".join(retrieved_texts)

    final_prompt = f"""You are Jarvis. Answer the User Question using ONLY the provided Historical Context. 
If the answer cannot be found in the context, say "I don't remember any events matching this."

Historical Context:
{combined_context}

User Question: {user_question}"""

    return final_prompt, retrieved_metadatas