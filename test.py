from pathlib import Path
import json
blog = "sassymamasg"

rss_path = Path("articles_output") / f"{blog}_articles.json"

with open(rss_path, 'r', encoding='utf-8') as f:
    rss_data = json.load(f)

print(len(rss_data))