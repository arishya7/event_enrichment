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
    parser.add_argument('function', choices=['review', 'merge', 'upload', 'cleanup', 'browse'], 
                       help='Function to run: review, merge, upload, cleanup, or browse')
    parser.add_argument('--folder-name', help='Folder name to use as timestamp (for review, merge, and upload functions)')
    
    args = parser.parse_args()
    
    try:
        if args.function == 'review':
            # Use folder_name as timestamp for review function
            if not args.folder_name:
                print("❌ Error: --folder-name is required for review function")
                print("Usage: python run_individual_functions.py review --folder-name <folder_name>")
                sys.exit(1)
            
            run = Run(timestamp=args.folder_name)
            print(f"🔍 Starting event review process for folder: {args.folder_name}")
            run.handle_events_review(Path('data/events_output'))
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
            
            # Use folder_name as timestamp for upload function
            if not args.folder_name:
                print("❌ Error: --folder-name is required for upload function")
                print("Usage: python run_individual_functions.py upload --folder-name <folder_name>")
                sys.exit(1)
            
            run = Run(timestamp=args.folder_name)
            print(f"📁 Using folder name: {args.folder_name}")
            run.upload_to_s3(None)
            print("✅ S3 upload completed!")
                
        elif args.function == 'cleanup':
            print("🧹 Starting cleanup process...")
            from src.utils.file_utils import cleanup_temp_folders
            run = Run(timestamp="9_temp_folder")
            cleanup_temp_folders(run.feed_dir, run.articles_output_dir)
            print("✅ Cleanup completed!")
            
        elif args.function == 'browse':
            print("🌐 Starting S3 interactive browser...")
            from src.services.aws_s3 import S3
            s3 = S3()
            s3.run_interactive()
            print("✅ S3 browser session ended!")
            
    except KeyboardInterrupt:
        print("\n❌ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 