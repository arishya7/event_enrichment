# web-scraping

Project Root/
│
├── articles_output/
│   │   # Contains JSON files, where each file represents articles scraped from a specific blog.
│   │   # Naming convention: {blog_name}_articles.json
│   │
│   ├── blog_A_articles.json
│   │       └─ [ 
│   │            { "title": "Article 1 Title", "url": "...", "content": "...", "published_date": "..." },
│   │            { "title": "Article 2 Title", "url": "...", "content": "...", "published_date": "..." },
│   │            ... 
│   │          ]
│   ├── blog_B_articles.json
│   │       └─ [ ... ] 
│   └── ...
│
├── events_output/
│   │   # Contains JSON files, where each file represents events extracted from the articles of a specific blog.
│   │   # Also contains a subdirectory for images related to these events.
│   │   # Naming convention for event files: {blog_name}_events.json
│   │
│   ├── images/
│   │   │   # Contains subdirectories for each blog, storing downloaded images for events.
│   │   │   # Naming convention for image files might be: {event_title}_{image_index}.{extension}
│   │   │
│   │   ├── blog_A/
│   │   │   ├── Event_Title_1_1.jpg
│   │   │   ├── Event_Title_1_2.png
│   │   │   └── ...
│   │   ├── blog_B/
│   │   │   └── ...
│   │   └── image_mapping.json # (Optional) A JSON file mapping event titles or IDs to their downloaded image paths/URLs.
│   │ 
│   ├── blog_A_events.json
│   │       └─ [
│   │            { 
│   │              "title": "Event 1 Title", 
│   │              "description": "...", 
│   │              "venue_name": "...", # Or "venue"
│   │              "full_address": "...", 
│   │              "latitude": 1.234, 
│   │              "longitude": 103.800,
│   │              "event_date": "YYYY-MM-DD", 
│   │              "event_time": "HH:MM",
│   │              "price": "...",
│   │              "url": "...", # Original article URL or event-specific URL
│   │              "images": [
│   │                  {"local_path": "events_output/images/blog_A/Event_Title_1_1.jpg", "original_url": "..."},
│   │                  ...
│   │              ],
│   │              "datetime_scraped_on": "YYYY-MM-DDTHH:MM:SS.ffffff" # Timestamp of when this event was processed
│   │            },
│   │            ...
│   │          ]
│   ├── blog_B_events.json
│   │       └─ [ ... ]
│   └── ...
│
├── RSS_temp/
│   │   # Temporary storage for downloaded RSS feed XML files.
│   │   # Naming convention: {blog_name}.xml
│   │
│   ├── blog_A.xml
│   ├── blog_B.xml
│   └── ...
│
├── metadatabase/ 
│   │   # (Conceptually, this might be a single file or a simple database, e.g., a JSON file acting as a DB)
│   │   # Purpose: To keep track of processed articles to avoid re-processing them in subsequent runs.
│   │   # It likely stores identifiers of articles that have already been parsed and had events extracted.
│   │   # If it's a file, it might be named something like `processed_articles_meta.json` or `run_history.json`.
│   │
│   └── processed_articles_meta.json 
│           └─ {
│                "run_history": [
│                    {"timestamp": "YYYY-MM-DDTHH:MM:SS.ffffff", "articles_processed_count": X},
│                    ...
│                ],
│                "processed_article_urls": { 
│                    "blog_A_rss_file_path_or_id": [
│                        "url_of_article_1_from_blog_A",
│                        "url_of_article_2_from_blog_A",
│                        ...
│                    ],
│                    "blog_B_rss_file_path_or_id": [ ... ]
│                },
│                "last_successful_run": "YYYY-MM-DDTHH:MM:SS.ffffff" 
│              }
│              # The exact structure depends on how MetaDatabase is implemented. 
│              # It might store article URLs, GUIDs, or publication dates hashed per blog/feed.
│              # The `current_run["timestamp"]` you added seems to be related to this.
│
├── main.py                 # Main script to orchestrate the scraping and extraction.
├── articles_extractor.py   # Module for fetching and parsing articles from RSS feeds.
├── events_extractor.py     # Module for extracting event details from articles using Gemini API.
├── address_extractor.py    # Module for getting address details (lat/long) from venue names.
├── image_extractor.py      # Module for searching and downloading images for events.
├── blog_websites.txt       # Input file listing blog URLs and names.
├── event_schema_init.json  # JSON schema for the Gemini API event extraction.
├── system_instruction.txt  # System prompt/instructions for the Gemini API.
└── .env                    # Environment variables (API keys, etc.).