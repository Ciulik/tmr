import ollama
import os
from datetime import datetime

def generate_report(articles: list):
    # Guard clause: never generate an empty report if ingestion failed 
    if len(articles) == 0:
        print("No articles fetched. Skipping report generation.")
        return

    # Step 5 of the pipeline: Prompt construction 
    prompt = f"Summarize these {len(articles)} articles into a daily briefing. Categorize them by topic:\n\n"
    for a in articles:
        title = a.get("title", "No Title")
        summary = a.get("summary", "No Summary")
        prompt += f"- {title} ({a.get('_source')}): {summary}\n"

    print("Generating summary via Ollama...")
    
    # Step 6 of the pipeline: ollama.chat() 
    response = ollama.chat(model="llama3", messages=[
        {"role": "system", "content": "You are a personal assistant who loves Data Science, Jarvis from Tony Stark. Provide a clean, Markdown-formatted news summary."},
        {"role": "user", "content": prompt}
    ])
    
    # Step 7 of the pipeline: Markdown file saved to disk 
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_path = f"reports/{date_str}.md"
    
    # Ensure reports directory exists
    os.makedirs("reports", exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(response["message"]["content"])
        
    print(f"Report saved to {output_path} - Ready for Obsidian!")