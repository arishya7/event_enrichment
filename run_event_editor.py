import sys
from src.web_editor.app import launch_editor

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_event_editor.py <timestamp>")
        print("Example: python run_event_editor.py 20250704_144730")
        sys.exit(1)
    timestamp = sys.argv[1]
    launch_editor(timestamp)
    input("Press Enter to exit the editor...\n") 