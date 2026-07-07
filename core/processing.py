from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import spacy
from spacy import displacy


# Load the local embedding model
print("Loading all-MiniLM-L6-v2 model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Loading spaCy en_core_web_sm model...")
nlp = spacy.load("en_core_web_sm")

def embed_articles(articles: list[dict]) -> list[dict]:
    """Generates embeddings and stores them inside each article dict."""
    if not articles:
        return []
    
    # Create the text to embed (Headline + Summary)
    texts = [f"{a.get('title', '')} {a.get('summary', '')}" for a in articles]
    embeddings = model.encode(texts)
    
    # Store embedding AS PART OF the article dict
    for i, article in enumerate(articles):
        article["embedding"] = embeddings[i]
        
    return articles

def cluster_articles(articles: list[dict], threshold: float = 0.75) -> list[list[dict]]:
    """Groups articles with a cosine similarity > threshold into events."""
    if not articles:
        return []
        
    # Extract embeddings into a 2D matrix for sklearn
    embeddings_matrix = np.array([a["embedding"] for a in articles])
    
    # Calculate the similarity matrix using sklearn's pairwise metrics
    sim_matrix = cosine_similarity(embeddings_matrix)
    
    clusters = []
    assigned_indices = set()
    
    for i in range(len(articles)):
        if i in assigned_indices:
            continue
            
        # Start a new cluster with the current article
        current_cluster = [articles[i]]
        assigned_indices.add(i)
        
        # Find all other articles similar to this one
        for j in range(i + 1, len(articles)):
            if j not in assigned_indices and sim_matrix[i][j] > threshold:
                current_cluster.append(articles[j])
                assigned_indices.add(j)
                
        clusters.append(current_cluster)
        
    return clusters


#entity extraction

def merge_cluster(cluster: list[dict]) -> dict:
    """
    Transforms a list of similar articles into a single Event object.
    """
    # Guard clause: if the cluster is empty, return an empty dict
    if not cluster:
        return {}

    # 1. Primary Headline: Take the title of the first article in the cluster
    primary_headline = cluster[0].get("title", "No Title")

    # 2. Combined Summary: Concatenate text, keeping the source attached
    combined_summary_parts = []
    for article in cluster:
        source = article.get("_source", "Unknown Source")
        summary = article.get("summary", "")
        # Add the source name before the text, exactly as you suggested!
        combined_summary_parts.append(f"[{source}] {summary}")
    
    # Join all parts with a newline
    combined_summary_text = "\n".join(combined_summary_parts)

    # 3. Source Links: Extract all URLs, ignoring empty ones
    source_links = [article.get("link") for article in cluster if article.get("link")]

    # 4. Event Date: Grab the date of the first published article
    event_date = cluster[0].get("published", "Unknown Date")

    # Construct and return the final Event dictionary
    event = {
        "primary_headline": primary_headline,
        "combined_summary": combined_summary_text,
        "source_links": source_links,
        "event_date": event_date,
        "entities": extract_entities(combined_summary_text) # We filled out the keywords
    }

    return event


def extract_entities(text: str) -> list[str]:
    """
    Scans text and extracts unique People, Organizations, and Locations.
    """
    # 1. Pass the text through the spaCy model
    doc = nlp(text)
    
    # 2. Create an empty Python set to automatically handle deduplication
    unique_entities = set()
    
    # 3. Loop through all recognized entities in the document
    for ent in doc.ents:
        # 4. Filter strictly for ORG (Organizations), PERSON (People), and GPE (Locations)
        # Note: we use ent.label_ (with an underscore) to get the string name of the label
        if ent.label_ in ["ORG", "PERSON", "GPE"]:
            # 5. Add the actual text of the entity to our set
            unique_entities.add(ent.text)
            
    # Convert the set back to a list so it can be easily exported to JSON later
    return list(unique_entities)