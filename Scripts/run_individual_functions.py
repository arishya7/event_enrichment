#!/usr/bin/env python3
"""
Script to run individual functions from the Run class.
This prevents accidental input from disrupting the main run.start() process.
"""

import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from src.core.run import Run

def main():
    parser = argparse.ArgumentParser(description='Run individual functions from the Run class')
    parser.add_argument('function', choices=['review', 'merge', 'upload', 'cleanup'], 
                       help='Function to run: review, merge, upload, or cleanup')
    parser.add_argument('--events-output', help='Path to events output directory (default: data/events_output)', default='data/events_output')
    parser.add_argument('--merged-filepath', help='Path to merged events file (for upload function)')
    parser.add_argument('--folder-name', help='Folder name to use as timestamp (for review and merge functions)')
    
    args = parser.parse_args()
    
    try:
        if args.function == 'review':
            # Use folder_name as timestamp for review function
            if not args.folder_name:
                print("❌ Error: --folder-name is required for review function")
                print("Usage: python run_individual_functions.py review --folder-name <folder_name>")
                sys.exit(1)
            
            run = Run(timestamp=args.folder_name)
            print(f"🔍 Starting event review process in {args.events_output} for folder: {args.folder_name}")
            run.handle_events_review(Path(args.events_output))
            print("✅ Event review completed!")
            
        elif args.function == 'merge':
            # Use folder_name as timestamp for merge function
            if not args.folder_name:
                print("❌ Error: --folder-name is required for merge function")
                print("Usage: python run_individual_functions.py merge --folder-name <folder_name>")
                sys.exit(1)
            
            run = Run(timestamp=args.folder_name)
            print(f"🔄 Starting event merge process for folder: {args.folder_name}")
            merged_file = run.merge_events()
            if merged_file:
                print(f"✅ Events merged successfully: {merged_file}")
            else:
                print("❌ Event merge cancelled or failed")
                
        elif args.function == 'upload':
            print("☁️ Starting S3 upload process...")
            merged_file_path = None
            
            # Check if merged file path was provided
            if args.merged_filepath:
                merged_file_path = Path(args.merged_filepath)
            else:
                print("⚠️ No merged file specified. Please provide --merged-filepath argument")
                print("Usage: python run_individual_functions.py upload --merged-filepath <path_to_merged_file>")
                sys.exit(1)
            
            if merged_file_path and merged_file_path.exists():
                # Extract folder name from the merged file path
                # Get the immediate parent directory name
                folder_name = merged_file_path.parent.name
                print(f"📁 Extracted folder name: {folder_name}")
                run = Run(timestamp=folder_name)
                run.upload_to_s3(merged_file_path)
                print("✅ S3 upload completed!")
            else:
                print("❌ Cannot upload: merged file not found")
                
        elif args.function == 'cleanup':
            print("🧹 Starting cleanup process...")
            from src.utils.file_utils import cleanup_temp_folders
            cleanup_temp_folders(run.feed_dir, run.articles_output_dir)
            print("✅ Cleanup completed!")
            
    except KeyboardInterrupt:
        print("\n❌ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 