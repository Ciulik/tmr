import json
import os
import datetime
from core.ingestion import fetch_all_feeds
from core.processing import embed_articles, cluster_articles, merge_cluster
from core.intelligence import generate_report
from core.memory import store_event, dump_to_json

MAX_EVENTS_TOTAL = 25


def get_or_fetch_raw_articles(sources: list[dict], raw_filepath: str):
    """
    Avoids hammering RSS feeds on every re-run. If today's raw dump
    already exists, asks before refetching; otherwise reuses what's
    on disk with zero network calls.
    """
    if os.path.exists(raw_filepath):
        print(f"\n📦 Found existing raw data for today: {raw_filepath}")
        choice = input(
            "Re-fetch from feeds and overwrite it? "
            "Type 'Yes' to refetch, or press Enter to reuse cached data: "
        ).strip()

        if choice.lower() == "yes":
            print("Refetching from RSS feeds...")
            articles, failed_sources = fetch_all_feeds(sources)
            return articles, failed_sources, True

        print("Reusing cached raw data from disk — no network calls made.")
        with open(raw_filepath, "r", encoding="utf-8") as f:
            articles = json.load(f)
        return articles, [], False

    print("Fetching feeds...")
    articles, failed_sources = fetch_all_feeds(sources)
    return articles, failed_sources, True


def main():
    print("==================================================")
    print("🚀 JARVIS OS - DAILY PIPELINE INITIALIZING...")
    print("==================================================")

    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # Step 1: Load config.
    print("Loading configuration...")
    try:
        with open("config/sources.json", "r", encoding="utf-8") as f:
            sources = json.load(f)
    except FileNotFoundError:
        print("Error: config/sources.json not found. Did you create it?")
        return
    except json.JSONDecodeError as e:
        print(f"Error: config/sources.json has invalid JSON syntax: {e}")
        return

    # Topics pulled FROM config, never retyped here — this is what keeps
    # a config typo (like "Geopolitic") from ever silently mismatching
    # against a hardcoded list somewhere else in the code.
    topics = sorted({s.get("topic") for s in sources if s.get("topic")})
    print(f"Topics found in config: {topics}")

    # Step 2: Ingestion — cache-aware, asks before refetching.
    raw_filepath = f"data/raw/{current_date}-raw.json"
    articles, failed_sources, freshly_fetched = get_or_fetch_raw_articles(sources, raw_filepath)

    if failed_sources:
        print(f"Warning: Failed to fetch from {failed_sources}")

    # SAVE POINT 1: only re-save if this run actually hit the network —
    # no point rewriting the exact file we just read from.
    if articles and freshly_fetched:
        dump_to_json(articles, raw_filepath)

    # Step 3: Basic Filter/Clean.
    cleaned_articles = [
        a for a in articles
        if a.get("title", "").strip() and a.get("summary", "").strip()
    ]

    if not cleaned_articles:
        print("No valid articles remained after cleaning. Exiting.")
        return

    # Sanity check kept as a safety net: if a future feed gets added to
    # sources.json with a typo'd topic, this is what surfaces it instead
    # of letting it silently vanish.
    known_topics = set(topics)
    orphaned = [a for a in cleaned_articles if a.get("topic") not in known_topics]
    if orphaned:
        bad_topics = {a.get("topic") for a in orphaned}
        print(f"⚠️ {len(orphaned)} articles have an unrecognized topic and "
              f"will be skipped: {bad_topics}")

    # Step 4: Processing Layer.
    print(f"Processing {len(cleaned_articles)} raw articles...")

    # Embed ONCE across everything — the model doesn't care about topic,
    # so splitting this step by topic would just multiply overhead.
    embedded_articles = embed_articles(cleaned_articles)

    # Daily event budget split evenly across topics, so one noisy topic
    # (Health had 60 clusters!) can't crowd out a quieter one.
    max_per_topic = max(1, MAX_EVENTS_TOTAL // len(topics)) if topics else MAX_EVENTS_TOTAL

    all_events = []          # flat list -> JSON backup + report
    event_cluster_pairs = [] # (event, cluster) kept together -> memory storage

    for topic in topics:
        print(f"\n--- Processing Topic: {topic} ---")
        topic_articles = [a for a in embedded_articles if a.get("topic") == topic]

        if not topic_articles:
            print(f"No articles for topic '{topic}' today.")
            continue

        # Clustering scoped to this topic only, so a Financial story and
        # a Geopolitics story about a related event can't accidentally merge.
        clusters = cluster_articles(topic_articles)

        pairs = []
        for cluster in clusters:
            combined_cluster_text = "\n\n".join(a.get("summary", "") for a in cluster)
            event = merge_cluster(cluster, generated_summary=combined_cluster_text)
            if event:
                event["topic"] = topic
                pairs.append((event, cluster))  # never separate these two

        # Rank within this topic, then cap. Source-link count as a rough
        # "more outlets covering it = more likely to matter" proxy.
        pairs.sort(key=lambda p: len(p[0].get("source_links", [])), reverse=True)
        pairs = pairs[:max_per_topic]

        print(f"  -> {len(pairs)} events kept for '{topic}' (of {len(clusters)} clustered)")

        all_events.extend(p[0] for p in pairs)
        event_cluster_pairs.extend(pairs)

    print(f"\nReduced {len(cleaned_articles)} raw articles into "
          f"{len(all_events)} events across {len(topics)} topics.")

    # ==========================================
    # MEMORY LAYER
    # ==========================================
    print("Writing events to ChromaDB Long-Term Memory...")
    for event, cluster in event_cluster_pairs:
        store_event(event, cluster=cluster)

    # SAVE POINT 2: processed events, including embeddings, for debugging/backup.
    if all_events:
        dump_to_json(all_events, f"data/processed/{current_date}-events.json")

    # Step 5: Intelligence Layer.
    print("Generating intelligent summary via Ollama...")
    generate_report(all_events)

    print("\n==================================================")
    print("✨ PIPELINE COMPLETE. JARVIS IS GOING TO SLEEP.")
    print("==================================================")


if __name__ == "__main__":
    main()