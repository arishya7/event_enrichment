"""
Interactive script to select and delete specific files from S3.

Usage:
    python delete_s3_files_selective.py <folder_path> [--dry-run]
    
Examples:
    # Select files to delete from a timestamp folder
    python delete_s3_files_selective.py 20251106_000000
    
    # Preview mode (dry run)
    python delete_s3_files_selective.py 20251106_000000 --dry-run
"""

import sys
from src.services.aws_s3 import S3

def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def main():
    if len(sys.argv) < 2:
        print("Usage: python delete_s3_files_selective.py <folder_path> [--dry-run]")
        print("\nExamples:")
        print("  python delete_s3_files_selective.py 20251106_000000")
        print("  python delete_s3_files_selective.py 20251106_000000 --dry-run")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    dry_run = '--dry-run' in sys.argv or '-dry-run' in sys.argv
    
    # Normalize path (handle Windows backslashes)
    folder_path = folder_path.replace('\\', '/')
    
    print(f"📂 Listing files in: {folder_path}")
    
    s3 = S3()
    success, files, message = s3.list_files_in_folder(folder_path)
    
    if not success:
        print(f"❌ {message}")
        sys.exit(1)
    
    if not files:
        print(f"✅ {message}")
        print("No files to delete.")
        sys.exit(0)
    
    print(f"\n✅ {message}")
    print("\n" + "="*70)
    print("Files in folder:")
    print("="*70)
    
    # Display files with numbers
    for i, file_info in enumerate(files, 1):
        size_str = format_file_size(file_info['Size'])
        key = file_info['Key']
        # Show just the filename if it's long
        display_key = key.split('/')[-1] if '/' in key else key
        if len(display_key) > 50:
            display_key = display_key[:47] + "..."
        print(f"  {i:3d}. {display_key:<50} ({size_str})")
    
    print("="*70)
    print(f"\nTotal: {len(files)} file(s)")
    
    # Get user selection
    print("\nSelect files to delete:")
    print("  - Enter file numbers separated by commas (e.g., 1,3,5-10,15)")
    print("  - Enter 'all' to select all files")
    print("  - Enter 'none' or press Enter to cancel")
    
    selection = input("\nYour selection: ").strip().lower()
    
    if not selection or selection == 'none':
        print("❌ Cancelled. No files selected.")
        sys.exit(0)
    
    # Parse selection
    selected_indices = set()
    if selection == 'all':
        selected_indices = set(range(1, len(files) + 1))
    else:
        try:
            parts = selection.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    # Range like "5-10"
                    start, end = map(int, part.split('-'))
                    selected_indices.update(range(start, end + 1))
                else:
                    # Single number
                    selected_indices.add(int(part))
        except ValueError:
            print("❌ Invalid selection format. Use numbers, ranges, or 'all'.")
            sys.exit(1)
    
    # Validate indices
    valid_indices = {i for i in selected_indices if 1 <= i <= len(files)}
    invalid = selected_indices - valid_indices
    if invalid:
        print(f"⚠️  Warning: Invalid file numbers ignored: {sorted(invalid)}")
    
    if not valid_indices:
        print("❌ No valid files selected.")
        sys.exit(0)
    
    # Get selected file keys
    selected_files = [files[i - 1]['Key'] for i in sorted(valid_indices)]
    
    print(f"\n📋 Selected {len(selected_files)} file(s) for deletion:")
    for i, key in enumerate(selected_files[:10], 1):
        display_key = key.split('/')[-1] if '/' in key else key
        if len(display_key) > 60:
            display_key = display_key[:57] + "..."
        print(f"   {i}. {display_key}")
    if len(selected_files) > 10:
        print(f"   ... and {len(selected_files) - 10} more")
    
    # Delete selected files
    success, message, count = s3.delete_selected_files(selected_files, confirm=True, dry_run=dry_run)
    
    print(f"\n{message}")
    if success:
        if dry_run:
            print(f"📊 Would delete {count} file(s) (DRY RUN - nothing was actually deleted)")
        else:
            print(f"📊 Deleted {count} file(s)")
    else:
        print("\n❌ Deletion failed. Check the error message above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

