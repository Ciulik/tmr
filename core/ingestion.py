import feedparser
import logging
from datetime import datetime

# Learner note: logging.warning()/logging.error() calls only actually get printed
# if logging is "configured." Without this line, Python uses a bare-bones default
# that can behave inconsistently depending on how the script is run.
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def fetch_all_feeds(sources: list[dict]) -> tuple:
    articles = []
    failed_sources = []

    for source in sources:
        try:
            # Step 1: Parse the RSS feed URL.
            feed = feedparser.parse(source["url"])

            # Step 2: feedparser almost never raises exceptions itself — even a broken
            # or malformed feed usually just returns an empty/partial result.
            # feed.bozo is feedparser's own way of flagging "something was wrong while parsing."
            # We check it explicitly instead of relying on an exception that may never come.
            if feed.bozo:
                logging.warning(
                    f"MALFORMED FEED: {source.get('name', 'Unknown')} | {feed.bozo_exception}"
                )

            # Step 3: Guard against silently empty feeds (e.g. feed URL is fine, but has no articles).
            if not feed.entries:
                logging.warning(f"EMPTY: {source.get('name', 'Unknown')}")
                failed_sources.append(source.get("name", "Unknown"))
            else:
                for entry in feed.entries:
                    entry["source"] = source.get("name", "Unknown")
                    entry["topic"] = source.get("topic", "General")
                articles.extend(feed.entries)

        except KeyError as e:
            # Specifically catches the case where a source dict is missing "url" or "name"
            # in your sources.json config — a config typo shouldn't crash the whole fetch.
            logging.error(f"CONFIG ERROR: source is missing a required key: {e}")
            failed_sources.append(source.get("name", "Unknown source"))

        except Exception as e:
            # Catch-all for anything else unexpected (network timeout, DNS failure, etc.)
            # so that one bad feed doesn't stop the other feeds from being fetched.
            logging.error(f"FAILED: {source.get('name', 'Unknown')} | {e}")
            failed_sources.append(source.get("name", "Unknown"))

    return articles, failed_sources