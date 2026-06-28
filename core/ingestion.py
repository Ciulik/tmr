import feedparser
import logging
from datetime import datetime

def fetch_all_feeds(sources: list[dict]) -> tuple:
    articles = []
    failed_sources = []
    
    for source in sources:
        try:
            # Step 2 of the pipeline: parse the URL 
            feed = feedparser.parse(source["url"])
            
            # Guard against silent empty returns
            if not feed.entries:
                logging.warning(f"[{datetime.now()}] EMPTY: {source['name']}")
                failed_sources.append(source["name"])
            else:
                for entry in feed.entries:
                    entry["_source"] = source["name"]
                    entry["_topic"] = source.get("topic", "General")
                articles.extend(feed.entries)
                
        except Exception as e:
            # Step 3 of the pipeline: loop + try/except 
            logging.error(f"[{datetime.now()}] FAILED: {source['name']} | {e}")
            failed_sources.append(source["name"])
            
    # Returns a tuple of raw entries and failed sources
    return articles, failed_sources