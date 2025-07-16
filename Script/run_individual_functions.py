#!/usr/bin/env python3
"""
Script to run individual functions from the Run class.
This prevents accidental input from disrupting the main run.start() process.
"""

import sys
import argparse
from pathlib import Path
from src.core.run import Run

def main():
    parser = argparse.ArgumentParser(description='Run individual functions from the Run class')
    parser.add_argument('function', choices=['review', 'merge', 'upload', 'cleanup'], 
                       help='Function to run: review, merge, upload, or cleanup')
    parser.add_argument('--timestamp', required=True, help='Timestamp for the run (e.g., 20250715_103130)')
    parser.add_argument('--merged-file', help='Path to merged events file (for upload function)')
    
    args = parser.parse_args()
    
    # Create Run instance
    run = Run(args.timestamp)
    
    try:
        if args.function == 'review':
            print("🔍 Starting event review process...")
            run.handle_events_review()
            print("✅ Event review completed!")
            
        elif args.function == 'merge':
            print("🔄 Starting event merge process...")
            merged_file = run.merge_events()
            if merged_file:
                print(f"✅ Events merged successfully: {merged_file}")
                # Save the merged file path for later use
                with open('.last_merged_file', 'w') as f:
                    f.write(str(merged_file))
            else:
                print("❌ Event merge cancelled or failed")
                
        elif args.function == 'upload':
            print("☁️ Starting S3 upload process...")
            merged_file_path = None
            
            # Check if merged file path was provided
            if args.merged_file:
                merged_file_path = Path(args.merged_file)
            else:
                # Try to get the last merged file
                try:
                    with open('.last_merged_file', 'r') as f:
                        merged_file_path = Path(f.read().strip())
                except FileNotFoundError:
                    print("⚠️ No merged file found. Run merge first or provide --merged-file")
            
            if merged_file_path and merged_file_path.exists():
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