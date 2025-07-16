#!/usr/bin/env python3
"""
Simple runner script for individual Run class functions.
Usage: python run.py <function> <timestamp> [options]
"""

import sys
import os
import subprocess
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path.cwd()))

def show_usage():
    print("Usage: python run.py <function> <timestamp> [options]")
    print()
    print("Functions:")
    print("  review    - Launch event review/edit interface")
    print("  merge     - Merge events into a single file")
    print("  upload    - Upload files to AWS S3")
    print("  cleanup   - Clean up temporary files")
    print()
    print("Options:")
    print("  --merged-file <path>   Path to merged events file (for upload)")
    print()
    print("Examples:")
    print("  python run.py review 20250715_103130")
    print("  python run.py merge 20250715_103130")
    print("  python run.py upload 20250715_103130")
    print("  python run.py upload 20250715_103130 --merged-file data/events.json")
    print("  python run.py cleanup 20250715_103130")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        show_usage()
        sys.exit(1)
    
    # Pass all arguments to the individual functions script
    args = ["python", "run_individual_functions.py"] + sys.argv[1:]
    
    # Execute the command
    try:
        result = subprocess.run(args, check=True)
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n❌ Process interrupted by user")
        sys.exit(1) 