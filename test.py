from pathlib import Path

blog = "sassymamasg"

rss_path = Path("articles_output") / blog+".json"
event_path = Path("events_output") / f"{blog}_events.json"

print(f"RSS file exists: {rss_path.exists()}")
print(f"Event file exists: {event_path.exists()}")