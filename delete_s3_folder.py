"""
Script to delete a folder from S3.

Usage:
    python delete_s3_folder.py <folder_path> [--dry-run] [--no-confirm]
    
Examples:
    # Preview what would be deleted (dry run)
    python delete_s3_folder.py 20251106_000000 --dry-run
    
    # Delete images folder for a specific timestamp
    python delete_s3_folder.py 20251106_000000
    
    # Delete full path
    python delete_s3_folder.py s3fs-private/events_output/20251106_000000/images/
    
    # Delete without confirmation (dangerous!)
    python delete_s3_folder.py 20251106_000000 --no-confirm
"""

import sys
from src.services.aws_s3 import S3

def main():
    if len(sys.argv) < 2:
        print("Usage: python delete_s3_folder.py <folder_path> [--dry-run] [--no-confirm]")
        print("\nExamples:")
        print("  # Preview what would be deleted (dry run):")
        print("  python delete_s3_folder.py 20251106_000000 --dry-run")
        print("\n  # Delete images for timestamp (auto-detects path):")
        print("  python delete_s3_folder.py 20251106_000000")
        print("\n  # Delete with full path:")
        print("  python delete_s3_folder.py s3fs-private/events_output/20251106_000000/images/")
        print("\n  # Delete without confirmation:")
        print("  python delete_s3_folder.py 20251106_000000 --no-confirm")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    dry_run = '--dry-run' in sys.argv or '-dry-run' in sys.argv
    confirm = '--no-confirm' not in sys.argv and not dry_run  # No confirmation needed for dry-run
    
    if dry_run:
        print(f"🔍 [DRY RUN] Previewing what would be deleted: {folder_path}")
    else:
        print(f"🗑️  Preparing to delete folder: {folder_path}")
        if not confirm:
            print("⚠️  WARNING: Confirmation is disabled!")
    
    s3 = S3()
    success, message, count = s3.delete_folder(folder_path, confirm=confirm, dry_run=dry_run)
    
    print(f"\n{message}")
    if success:
        if dry_run:
            print(f"📊 Would delete {count} object(s) (DRY RUN - nothing was actually deleted)")
        else:
            print(f"📊 Deleted {count} object(s)")
    else:
        print("\n❌ Operation failed. Check the error message above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

