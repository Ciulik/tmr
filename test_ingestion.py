import feedparser
import logging
import json
from datetime import datetime

# Setăm logging pentru a vedea erorile live
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def fetch_all_feeds(sources: list[dict]) -> tuple:
    articles = []
    failed_sources = []
    
    for source in sources:
        try:
            logging.info(f"Conectare la {source['name']}...")
            feed = feedparser.parse(source["url"])
            
            # Guard clause împotriva silent failures
            if not feed.entries:
                logging.warning(f"[{datetime.now()}] GOL: {source['name']} nu a returnat nimic.")
                failed_sources.append(source["name"])
            else:
                for entry in feed.entries:
                    # Normalizăm datele
                    clean_article = {
                        "_source": source["name"],
                        "_topic": source.get("topic", "General"),
                        "title": entry.get("title", "Fără Titlu"),
                        "link": entry.get("link", "Fără Link")
                    }
                    articles.append(clean_article)
                logging.info(f"-> Succes: {len(feed.entries)} articole extrase din {source['name']}.")
                
        except Exception as e:
            logging.error(f"[{datetime.now()}] EROARE MAJORĂ: {source['name']} | Detalii: {e}")
            failed_sources.append(source["name"])
            
    return articles, failed_sources

if __name__ == "__main__":
    print("\n--- INIȚIERE STRESS TEST: INGESTION LAYER v0.1 ---\n")
    
    # Încărcăm config-ul
    try:
        with open("config/sources.json", "r") as f:
            sources = json.load(f)
    except FileNotFoundError:
        print("Eroare: Nu am găsit config/sources.json. Asigură-te că fișierul există.")
        exit(1)
        
    # Rulăm funcția
    raw_articles, failures = fetch_all_feeds(sources)
    
    print("\n--- REZULTATE STRESS TEST ---")
    print(f"Total articole extrase (Raw JSON): {len(raw_articles)}")
    print(f"Surse care au eșuat (dacă există): {failures}")
    
    if len(raw_articles) > 0:
        print("\nExemplu - Primele 2 articole structurate în memorie:")
        print(json.dumps(raw_articles[:2], indent=2, ensure_ascii=False))