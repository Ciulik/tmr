import json
from core.ingestion import fetch_all_feeds
from core.intelligence import generate_report

def main():
    # 1. Load config 
    with open("config/sources.json", "r") as f:
        sources = json.load(f)
        
    # 2. Ingest
    print("Fetching feeds...")
    articles, failed_sources = fetch_all_feeds(sources)
    
    if failed_sources:
        print(f"Warning: Failed to fetch from {failed_sources}")
        
    # 3. Basic Filter/Clean 
    # Remove entries with no title or summary
    cleaned_articles = [a for a in articles if 'title' in a and 'summary' in a]
    
    # 4. Generate & Save
    generate_report(cleaned_articles)

if __name__ == "__main__":
    main()