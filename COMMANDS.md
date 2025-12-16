# Available Commands & Scripts

This document lists all available commands for running specific parts of the web scraping pipeline.

## Main Pipeline

### Full Pipeline Run
```bash
# Run full pipeline for all blogs
python main.py

# Run for a specific blog only
python main.py --blog thesmartlocal

# Run with custom timestamp
python main.py --timestamp 20250101_120000
```

## Individual Pipeline Steps

### 1. Event Review/Edit (Streamlit UI)
```bash
# Review and edit events in a browser interface
python Scripts/run_individual_functions.py review --folder-name 19Nov
# or
python run.py review 19Nov
```

### 2. Merge Events
```bash
# Merge all event JSON files from a timestamp folder into one file
python Scripts/run_individual_functions.py merge --folder-name 19Nov
# or
python run.py merge 19Nov
```

### 3. Upload to S3
```bash
# Upload processed files to AWS S3
python Scripts/run_individual_functions.py upload --folder-name 19Nov
# or
python run.py upload 19Nov
```

### 4. Cleanup Temporary Files
```bash
# Clean up temporary feed and article output folders
python Scripts/run_individual_functions.py cleanup
```

### 5. Browse S3
```bash
# Interactive S3 browser
python Scripts/run_individual_functions.py browse
```

## Data Processing Scripts

### Format JSON Files
```bash
# Clean and format JSON files (fix encoding, normalize paths)
python format_json.py data/events_output/19Nov
# Can also specify a single file
python format_json.py data/events_output/19Nov/marinabay.json
```

### Convert JSON to CSV
```bash
# Convert all JSON files in a folder to a single CSV
python json_to_csv.py data/events_output/19Nov output.csv
```

### Download Missing Images
```bash
# Download images referenced in JSON files
python download_missing_images.py data/events_output/19Nov/marinabay.json data/events_output/19Nov/images
```

### Add Image Paths to JSON
```bash
# Add local_path and filename to existing image objects in JSON
python add_image_paths.py data/events_output/19Nov data/events_output/19Nov/images
```

### Fix Image Filenames
```bash
# Fix image filenames (check file for usage)
python fix_image_filenames.py
```

## Testing Scripts

### Test Event Filtering
```bash
# Test semantic/topic-based event filtering logic
python test_filtering.py
```

### Test Playwright
```bash
# Test Playwright installation and functionality
python Scripts/test_playwright.py
# or
Scripts/test_playwright.bat
```

### Test URL
```bash
# Test URL validation/extraction
Scripts/test_url.bat
```

## S3 Management

### Delete S3 Folder
```bash
# Delete a folder from S3
python delete_s3_folder.py
```

### Delete S3 Files (Selective)
```bash
# Selectively delete files from S3
python delete_s3_files_selective.py
```

## Core Module Functions

You can also import and use individual functions from Python:

```python
from src.core.run import Run

# Create a run instance
run = Run(timestamp="19Nov", blog_name="bykido")

# Individual methods:
run.handle_events_review(Path('data/events_output'))  # Review events
run.merge_events()  # Merge events
run.upload_to_s3(merged_file_path)  # Upload to S3
run.deduplicate_events_semantic(events)  # Deduplicate events
```

## Common Workflows

### Test Event Extraction on Single Article
1. Run full pipeline but stop after extraction
2. Check `data/events_output/<timestamp>/relevant/` or `non-relevant/` folders

### Process Existing JSON Files
```bash
# 1. Format JSON files
python format_json.py data/events_output/19Nov

# 2. Download missing images
python download_missing_images.py data/events_output/19Nov/marinabay.json data/events_output/19Nov/images

# 3. Convert to CSV
python json_to_csv.py data/events_output/19Nov events_19Nov.csv
```

### Review and Merge Workflow
```bash
# 1. Review events
python Scripts/run_individual_functions.py review --folder-name 19Nov

# 2. Merge after review
python Scripts/run_individual_functions.py merge --folder-name 19Nov

# 3. Upload to S3
python Scripts/run_individual_functions.py upload --folder-name 19Nov
```

## Notes

- All scripts assume you're in the project root directory
- Most scripts require the virtual environment to be activated: `.venv/Scripts/Activate` (Windows) or `source venv/bin/activate` (Unix)
- Timestamp folders are typically in format: `YYYYMMDD_HHMMSS` or custom names like `19Nov`
- JSON files are usually in `data/events_output/<timestamp>/`
- Images are usually in `data/events_output/<timestamp>/images/`

