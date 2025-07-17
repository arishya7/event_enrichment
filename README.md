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
| **Honey Kids Asia** | https://honeykidsasia.com/feed/ |
| **Sassy Mama SG** | https://www.sassymamasg.com/feed/ |
| **Skoolopedia** | https://skoolopedia.com/feed/ |
| **Skoop SG** | https://skoopsg.com/feed/ |
| **The Asian Parent** | https://sg.theasianparent.com/feed/ |
| **The Honeycombers** | https://thehoneycombers.com/singapore/feed/ |
| **The New Age Parents** | https://thenewageparents.com/feed/ |
| **The Smart Local** | https://thesmartlocal.com/feed/ |

## Core Classes

### Core Classes (`src/core/`)
- **`Run`** - Main orchestrator class that manages the entire scraping pipeline
- **`Blog`** - Represents a blog with its feed URL and manages article extraction
- **`Article`** - Represents individual blog articles with content and metadata
- **`Event`** - Represents extracted family events with location, dates, and details

### Service Classes (`src/services/`)
- **`S3Uploader`** - Handles AWS S3 file uploads and directory management
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
git clone https://github.com/your-username/web-scraping-refactor.git
cd web-scraping-refactor
```

2. **Download requirements files:**
   - Download `requirements_main.txt` for the main processing pipeline
   - Download `requirements_app.txt` for the web application interface
   - Place both files in the project root directory

3. **Create virtual environments:**
```bash
# For main processing
python -m venv venv_main
source venv_main/bin/activate  # On Windows: venv_main\Scripts\activate
pip install -r requirements_main.txt

# For web app
python -m venv venv_app
source venv_app/bin/activate   # On Windows: venv_app\Scripts\activate
pip install -r requirements_app.txt
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
python main.py
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

### Run the AWS S3 Service
To use the AWS S3 service for uploading or managing files:
```bash
python -m src.services.aws_s3
```

## Running Individual Functions with Scripts

You can run individual functions (review, merge, upload, cleanup) using the same input format for all platforms:

- **Windows Batch (.bat)**
- **PowerShell (.ps1)**
- **Shell Script (.sh)**

**Usage:**
```bash
# General format for all scripts
<run_script> <function> <timestamp> [options]
```
Where:
- `<run_script>` is one of:
  - `Script/run_functions.bat` (Windows Batch)
  - `Script/run_functions.ps1` (PowerShell)
  - `Script/run_functions.sh`  (Shell/Bash)
- `<function>` is one of: `review`, `merge`, `upload`, `cleanup`
- `<timestamp>` is the run timestamp (e.g., `20250715_103130`)
- `[options]` are additional options, such as `--merged-file <path>` for upload

**Examples:**
```bash
# Launch event review interface
Script/run_functions.bat review YYYYMMDD_HHMMSS

# Merge events into a single file
Script/run_functions.bat merge YYYYMMDD_HHMMSS

# Upload to AWS S3
Script/run_functions.bat upload YYYYMMDD_HHMMSS --merged-file data/XXXX.json

# Clean up temporary files
Script/run_functions.bat cleanup YYYYMMDD_HHMMSS
```

## Directory Structure

```
web-scraping-refactor/
├── data/                     # Data storage
│   ├── events_output/        # Timestamped event outputs
│   ├── temp/                 # Temporary processing files
│   └── guid.db              # SQLite database
├── config/                   # Configuration files
├── src/                      # Source code
│   ├── core/                # Core business logic
│   ├── services/            # External service integrations
│   ├── ui/                  # Web interface components
│   └── utils/               # Utility functions
├── Script/                   # Platform-specific scripts
└── requirements_*.txt        # Dependencies
```

## Architecture Diagram

![Architecture Diagram](./assets/Architecture_diagram.svg)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
