import json
from pathlib import Path

# Initialize empty list to store all events
all_events = []

# Get all JSON files from events_output directory
events_dir = Path("events_output/20250612_131316")
json_files = list(events_dir.glob("*.json"))

# Read each JSON file and combine their contents
for json_file in json_files:
    print(f"Reading {json_file.name}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        events_data = json.load(f)
        all_events.extend(events_data)

print(f"\nTotal events collected: {len(all_events)}")

# Save combined events to events.json in root directory
output_file = Path("events.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_events, f, indent=2, ensure_ascii=False)

print(f"\nCombined events saved to {output_file}")
print(f"File size: {output_file.stat().st_size / 1024:.2f} KB")
