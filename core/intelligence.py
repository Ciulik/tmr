import ollama
import os
from datetime import datetime

def generate_report(events: list):
    # Guard clause: never generate an empty report if ingestion failed 
    if len(events) == 0:
        print("No events fetched. Skipping report generation.")
        return

    max_events = 25
    events_to_process = events[:max_events]
    
    # Step 5 of the pipeline: Prompt construction 
    prompt = f"Summarize these {len(events)} major events into a daily briefing:\n\n"
    for event in events:
        prompt += f"## {event['primary_headline']}\n"
        prompt += f"Reported by: {', '.join(event['source_links'])}\n"
        prompt += f"Facts: {event['combined_summary']}\n\n"

    print("Generating summary via Ollama...")
    
    # Step 6 of the pipeline: ollama.chat() 
    response = ollama.chat(model="llama3", messages=[
        {"role": "system", "content": "You are Jarvis. You must strictly format the daily briefing using ONLY these headers: # Financial, # Technology, # Health, and # Geopolitics. If there is no news for a category, write 'No updates today'."},
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