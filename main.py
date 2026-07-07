import json
from core.ingestion import fetch_all_feeds
from core.processing import embed_articles, cluster_articles, merge_cluster
from core.intelligence import generate_report

def main():
    # 1. Load config 
    print("Loading configuration...")
    with open("config/sources.json", "r", encoding="utf-8") as f:
        sources = json.load(f)
        
    # 2. Ingestion Layer
    print("Fetching feeds...")
    articles, failed_sources = fetch_all_feeds(sources)
    
    if failed_sources:
        print(f"Warning: Failed to fetch from {failed_sources}")
        
    # 3. Basic Filter/Clean 
    # Remove entries with no title or summary to prevent empty vectors
    cleaned_articles = [a for a in articles if 'title' in a and 'summary' in a]
    
    # 4. Processing Layer (The Smart Engine)
    print(f"Processing {len(cleaned_articles)} raw articles...")
    
    # Generate vector embeddings for the articles
    embedded_articles = embed_articles(cleaned_articles)
    
    # Group identical stories together based on a 0.85 cosine similarity threshold
    clusters = cluster_articles(embedded_articles)
    
    # Merge each raw cluster into a single, clean Event object
    events = []
    for cluster in clusters:
        event = merge_cluster(cluster)
        if event:
            events.append(event)
            
    print(f"Reduced {len(cleaned_articles)} raw articles into {len(events)} unique semantic events.")
    
    # 5. Intelligence Layer
    # Pass the clean Event dictionaries to Ollama instead of the raw data dumps
    print("Generating intelligent summary via Ollama...")
    generate_report(events)

if __name__ == "__main__":
    main()