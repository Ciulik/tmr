import ollama
import os
from datetime import datetime

def generate_report(events: list):
    # Step 1: Guard clause — never call an LLM with nothing to summarize.
    # This also protects us from wasting a request if ingestion silently failed upstream.
    if len(events) == 0:
        print("No events fetched. Skipping report generation.")
        return

    # Step 2: Cap how many events we send to the LLM.
    # Prompts that are too long can get truncated by the model's context window,
    # or just cost more tokens/time than needed. 25 is a reasonable ceiling for a daily brief.
    max_events = 25
    events_to_process = events[:max_events]

    if len(events) > max_events:
        # Learner note: this isn't an error, just something worth knowing about —
        # print() is fine here since it's informational, not a failure.
        print(f"Note: {len(events)} events found, only processing the top {max_events}.")

    # Step 3: Build the prompt.
    # BUG FIX: this loop now iterates over events_to_process, not the full events list,
    # so the max_events cap you set above is actually respected.
    prompt = f"Summarize these {len(events_to_process)} major events into a daily briefing:\n\n"
    for event in events_to_process:
        # Defensive .get() calls: if merge_cluster() ever changes its output shape,
        # we don't want a KeyError to kill the whole report generation.
        headline = event.get("primary_headline", "Untitled Event")
        sources_data = event.get("source_links", [])

        source_names = []
        for s in sources_data:
            # Check if it's a dict (v0.3 format) or string (v0.1 fallback)
            if isinstance(s, dict):
                source_names.append(s.get("source", "Unknown"))
            else:
                source_names.append(str(s))

        summary = event.get("combined_summary", "No details available.")

        prompt += f"## {headline}\n"
        prompt += f"Reported by: {', '.join(source_names) if source_names else 'Unknown source'}\n"     
        prompt += f"Facts: {summary}\n\n"

    print("Generating summary via Ollama...")

    # Step 4: Call the local LLM.
    # This is the riskiest external call in the whole pipeline — Ollama might not be running,
    # the model might not be pulled locally, or the connection might just time out.
    # Wrapping in try/except means one failed call doesn't crash your whole main.py run.
    try:
        response = ollama.chat(model="llama3", messages=[
            {"role": "system", "content": (
                "You are Jarvis. You must strictly format the daily briefing using ONLY "
                "these headers: # Financial, # Technology, # Health, and # Geopolitics. "
                "If there is no news for a category, write 'No updates today'."
            )},
            {"role": "user", "content": prompt}
        ])
    except Exception as e:
        # ConnectionError is the most common cause (Ollama server not running),
        # but we catch broadly here since ollama's client can raise a few different types.
        print(f"Error: Could not reach Ollama. Is the Ollama server running? Details: {e}")
        return

    # Step 5: Safely extract the response content.
    # Even if the call succeeds, defensively check the shape before indexing into it —
    # a malformed response here would otherwise throw a confusing KeyError deep in the function.
    try:
        report_content = response["message"]["content"]
    except (KeyError, TypeError) as e:
        print(f"Error: Unexpected response format from Ollama: {e}")
        return

    # Step 6: Save the markdown file to disk.
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_path = f"reports/{date_str}.md"

    try:
        os.makedirs("reports", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)
    except OSError as e:
        # Covers permission errors, disk full, invalid path characters, etc.
        print(f"Error: Could not write report to {output_path}: {e}")
        return

    print(f"Report saved to {output_path} - Ready for Obsidian!")