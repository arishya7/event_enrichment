# Web Scraping Refactor - Singapore Family Event Extractor

## Overview

This project is a comprehensive web scraping system designed to extract family-friendly event information from popular Singapore parenting and family blogs. The system automatically:

1. **Scrapes RSS/Atom feeds** from multiple Singapore family blogs
2. **Extracts event information** using Google's Gemini AI to identify family activities
3. **Geocodes event locations** using Google Places API
4. **Downloads event images** and organizes them by blog source
5. **Provides a web interface** for manual review and editing of extracted events
6. **Merges and exports** events to JSON format
7. **Uploads results to AWS S3** for storage and distribution

The system is built with a modular architecture to handle the entire pipeline from feed scraping to final event publication.

## Blogs Being Scraped

The system currently scrapes **9 popular Singapore family blogs**:

| Blog | Feed URL |
|------|----------|
| **Bykido** | https://www.bykido.com/blogs/guides-and-reviews-singapore.atom/ |
| **HoneyKidsAsia** | https://honeykidsasia.com/feed/ |
| **SassyMama** | https://www.sassymamasg.com/feed/ |
| **Skoolopedia** | https://skoolopedia.com/feed/ |
| **Skoopsg** | https://skoopsg.com/feed/ |
| **The Asian Parent** | https://sg.theasianparent.com/feed/ |
| **The Honeycombers** | https://thehoneycombers.com/singapore/feed/ |
| **The New Age Parents** | https://thenewageparents.com/feed/ |
| **The Smart Local** | https://thesmartlocal.com/feed/ |
### Note: In the future, if you only care more about quality, focus on these three blogs: sassymama, the asian parent and bykido. The rest can don't scrape. With just these three blogs, you can curl with python WITHOUT needing javascript verifications (don't need to open the streamlit and copy and paste from the browser). The reason for 9 blogs is because BA team more quanitty over quality.
## Core Classes

### Core Classes (`src/core/`)
- **`Run`** - Main orchestrator class that manages the entire scraping pipeline
- **`Blog`** - Represents a blog with its feed URL and manages article extraction
- **`Article`** - Represents individual blog articles with content and metadata
- **`Event`** - Represents extracted family events with location, dates, and details

### Service Classes (`src/services/`)
- **`S3`** - Handles AWS S3 file uploads, directory management, and interactive browsing
- **`Places`** - Integrates with Google Places API for location geocoding
- **`GenerativeLanguage`** - Manages Google Gemini AI integration for event extraction
- **`CustomSearch`** - Handles custom search functionality

### UI Components (`src/ui/`)
- **`EventManager`** - Streamlit interface for reviewing and editing extracted events
- **`FeedManager`** - Manual feed management interface
- **`Components`** - Reusable UI components for the web interface

### Utility Classes (`src/utils/`)
- **`Config`** - Configuration management and settings
- **`FileUtils`** - File operations and directory management
- **`TextUtils`** - Text processing and URL extraction utilities
- **`OutputFormatter`** - Formatted console output and logging

## Database

The system uses **SQLite** for tracking processed articles and preventing duplicate processing.

**Database Schema:**
```sql
CREATE TABLE processed_articles (
    blog_name TEXT NOT NULL,
    post_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    num_events INTEGER DEFAULT 0,
    PRIMARY KEY (blog_name, post_id)
);
```

**Database Location:** `data/guid.db`

**Purpose:**
- Track which blog articles have been processed
- Prevent duplicate processing of the same articles
- Store event counts for each processed article
- Maintain processing history with timestamps

## Installation & Setup

1. **Clone the repository:**
```bash
git clone https://github.com/your-username/web-scraping.git
cd web-scraping
```

2. **Download requirements files:**
   - Download `requirements.txt` for the main processing pipeline
   - Place both files in the project root directory

3. **Create virtual environments:**
```bash
# For main processing
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

4. **Set up environment variables:**
   - Create a `.env` file in the `config/` folder
   - Add your API keys and credentials:
   ```bash
   # config/.env
   GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here
   GOOGLE_PLACES_API_KEY=your_places_api_key_here
   AWS_ACCESS_KEY_ID=your_aws_access_key_here
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
   ```

5. **Configure additional settings** in `config/config.json`:
   - Adjust blog sources if needed
   - Modify file paths and directories
   - Update AWS S3 bucket settings

6. **Run the main pipeline:**
```bash
python .\main.py
```

## Required API Keys & Services

To run this project, you'll need to set up the following services and obtain API keys:

### 1. Google Cloud Platform (GCP) API Key
- **Purpose**: Used for all Google Cloud services in this project
- **How to get**:
  1. Go to [Google Cloud Console](https://console.cloud.google.com/)
  2. Create a project (or use an existing one)
  3. Enable the following APIs for your project:
     - **Generative AI API** (Vertex AI / Gemini)
     - **Google Places API**
     - **Programmable Search API**
  4. Create an API key (from "APIs & Services > Credentials")
- **Variable**: `GOOGLE_API_KEY` (used for all GCP services)

### 2. AWS S3
- **Purpose**: Upload processed events and images to cloud storage (required)
- **How to get**:
  - Obtain your AWS S3 access keys and bucket information from your IT department or system administrator.
  - (Optional) If you do not already have access, you may create an [AWS account](https://aws.amazon.com/), set up IAM, and generate access keys.
- **Variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET`

### Environment File Structure
Create `config/.env` with the following structure:
```bash
# Google Cloud Platform (GCP) API Key (used for all GCP services)
GOOGLE_API_KEY=your_gcp_api_key_here

# AWS S3 (required)
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=ap-southeast-1
S3_BUCKET=your-bucket-name
```

## Running the Main Pipeline and Individual Services

### Run the Main Pipeline
To run the main scraping and processing pipeline:
```bash
python main.py
```

### Run the AWS S3 Viewer without needing AWS account
To view the AWS S3:
```bash
python .\aws_viewer.py
```

### Interactive S3 Browser
For an interactive S3 file browser experience:
```bash
# Using Python script
python Scripts/run_individual_functions.py browse

# Using Windows batch file
run_functions.bat browse
```

## Running Individual Functions with Scripts

You can run individual functions using either the Python script or the Windows batch file:

### Python Script Usage
```bash
# General format
python Scripts/run_individual_functions.py <function> [options]
```

### Windows Batch File Usage
```bash
# General format
Scripts\run_functions.bat <function> [folder_name]
```

### Available Functions
- `review` - Launch event review/edit interface
- `merge` - Merge events into a single file
- `upload` - Upload files to AWS S3
- `browse` - Interactive S3 file browser
- `cleanup` - Clean up temporary files

### Examples

**Python Script:**
```bash
# Launch event review interface
python Scripts/run_individual_functions.py review --folder-name 20250715_103130
python Scripts/run_individual_functions.py review --folder-name evergreen

# Merge events into a single file
python Scripts/run_individual_functions.py merge --folder-name 20250715_103130
python Scripts/run_individual_functions.py merge --folder-name evergreen

# Upload to AWS S3
python Scripts/run_individual_functions.py upload --folder-name 20250715_103130
python Scripts/run_individual_functions.py upload --folder-name evergreen

# Interactive S3 browser
python Scripts/run_individual_functions.py browse

# Clean up temporary files
python Scripts/run_individual_functions.py cleanup
```

**Windows Batch File:**
```bash
# Launch event review interface
run_functions.bat review 20250715_103130
run_functions.bat review evergreen

# Merge events into a single file
run_functions.bat merge 20250715_103130
run_functions.bat merge evergreen

# Upload to AWS S3
run_functions.bat upload 20250715_103130
run_functions.bat upload evergreen

# Interactive S3 browser
run_functions.bat browse

# Clean up temporary files
run_functions.bat cleanup
```

### Required Arguments
- **review, merge, upload**: Require a folder name (timestamp, evergreen, or non-evergreen)
- **browse, cleanup**: No arguments required

## Directory Structure

```
web-scraping/
├── data/                    # Data storage
│   ├── archive/             # All the data that has been pushed to s3
│   ├── events_output/       # event outputs
│   │   ├──<timestamp>/      # Weekly scraped data put here. After pushing to s3, put them into archive/events_output. The merged json put inside archive root folder.
│   │   ├──evergreen/        # evergreen data. Consist ofr both outdoor and indoor playgrounds
│   │   ├──non-evergreen/    # Non-evergreen data. Consist of dining, malls-related and attractions
│   ├── temp/                # Temporary processing files. Can be deleted after each run.
│   └── guid.db              # SQLite database
├── config/                  # Configuration files
├── src/                     # Source code
│   ├── core/                # Core business logic
│   ├── services/            # External service integrations
│   ├── ui/                  # Web interface components
│   └── utils/               # Utility functions
├── Scripts/                 # Platform-specific scripts
└── requirements.txt         # Dependencies
```

## Architecture Diagram

![Architecture Diagram](./assets/Architecture_diagram.svg)

## License

This project is licensed under the MIT License - see the LICENSE file for details.