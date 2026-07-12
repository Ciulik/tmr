from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import spacy
import uuid  # NEW: needed to generate a unique cluster_id per event

print("Loading all-MiniLM-L6-v2 model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Loading spaCy en_core_web_sm model...")
nlp = spacy.load("en_core_web_sm")

def embed_articles(articles: list[dict]) -> list[dict]:
    """
    Generates embeddings and stores them inside each article dictionary.
    """
    if not articles:
        return []
    
    texts = [f"{a.get('title', '')} {a.get('summary', '')}" for a in articles]
    embeddings = model.encode(texts)
    
    for i, article in enumerate(articles):
        article["embedding"] = embeddings[i].tolist() 
        
    return articles

def cluster_articles(articles: list[dict], threshold: float = 0.75) -> list[list[dict]]:
    """
    Groups articles with a cosine similarity > threshold into clusters.
    """
    if not articles:
        return []
        
    embeddings_matrix = np.array([a["embedding"] for a in articles])
    sim_matrix = cosine_similarity(embeddings_matrix)
    
    clusters = []
    assigned_indices = set()
    
    for i in range(len(articles)):
        if i in assigned_indices:
            continue
            
        current_cluster = [articles[i]]
        assigned_indices.add(i)
        
        for j in range(i + 1, len(articles)):
            if j not in assigned_indices and sim_matrix[i][j] > threshold:
                current_cluster.append(articles[j])
                assigned_indices.add(j)
                
        clusters.append(current_cluster)
        
    return clusters

def extract_entities(text: str) -> list[str]:
    """
    Scans text and extracts unique People, Organizations, and Locations.
    """
    doc = nlp(text)
    unique_entities = set()
    for ent in doc.ents:
        if ent.label_ in ["ORG", "PERSON", "GPE"]:
            unique_entities.add(ent.text)
    return list(unique_entities)

def merge_cluster(cluster: list[dict], generated_summary: str) -> dict:
    """
    Transforms a cluster of similar articles into a single, clean Event object.
    Includes the LLM summary and a cluster-wide averaged embedding.
    """
    if not cluster:
        return {}

    # NEW: one ID shared by this event AND every article that built it.
    # This is what lets memory.py store articles separately from the
    # merged event, while still being able to trace "which articles
    # made up event X" — a real lookup instead of reconstructed text.
    cluster_id = str(uuid.uuid4())

    primary_headline = cluster[0].get("title", "No Title")
    dynamic_source_links = []
    
    for idx, article in enumerate(cluster):
        source = article.get("source", article.get("_source", f"Source {idx+1}"))
        dynamic_source_links.append({
            "source": source,
            "title": article.get("title", "No Title"),
            "url": article.get("link", "")
        })
    
    event_date = cluster[0].get("published", cluster[0].get("date", "Unknown Date"))
    
    # CHANGED: average every article's embedding instead of only keeping
    # cluster[0]'s. Why this matters: if the seed article (index 0) is a
    # short wire brief and article[3] is the full deep-dive, using only
    # article[0]'s vector under-represents what the merged event is
    # really about. np.mean collapses all N vectors into one point that
    # still lives in the same 384-dimensional space — a cheap, standard
    # way to represent "the whole cluster" as a single embedding.
    valid_embeddings = [a["embedding"] for a in cluster if a.get("embedding")]
    event_embedding = (
        np.mean(valid_embeddings, axis=0).tolist() if valid_embeddings else None
    )

    event = {
        "cluster_id": cluster_id,  # NEW
        "primary_headline": primary_headline,
        "combined_summary": generated_summary, 
        "source_links": dynamic_source_links, 
        "event_date": event_date,
        "entities": extract_entities(generated_summary), 
        "embedding": event_embedding 
    }

    # NEW: stamp the same cluster_id onto every raw article in the
    # cluster. memory.py's store_articles() reads this field to tag
    # each stored article with the event it belongs to.
    for article in cluster:
        article["cluster_id"] = cluster_id

    return event