import time

from src.core.run import Run

def main():
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run = Run(timestamp)
    run.start()

if __name__ == "__main__":
    main()