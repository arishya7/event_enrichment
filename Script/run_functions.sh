#!/bin/bash

# Script to run individual functions from the Run class
# This prevents accidental input from disrupting the main run.start() process

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

print_success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 <function> [timestamp] [options]"
    echo ""
    echo "Functions:"
    echo "  review    - Launch event review/edit interface"
    echo "  merge     - Merge events into a single file"
    echo "  upload    - Upload files to AWS S3"
    echo "  cleanup   - Clean up temporary files"
    echo ""
    echo "Options:"
    echo "  --merged-file <path>   Path to merged events file (for upload)"
    echo ""
    echo "Examples:"
    echo "  $0 review                               # Will prompt for timestamp"
    echo "  $0 review 20250715_103130              # Use specific timestamp"
    echo "  $0 merge"
    echo "  $0 upload"
    echo "  $0 upload 20250715_103130 --merged-file data/events.json"
    echo "  $0 cleanup"
}

# Check if minimum arguments are provided
if [ $# -lt 1 ]; then
    print_error "Insufficient arguments provided"
    show_usage
    exit 1
fi

FUNCTION=$1
shift 1

# Get timestamp - either from command line or user input
if [ -z "$1" ]; then
    print_info "Available timestamps:"
    if [ -d "data/events_output" ]; then
        ls -1 data/events_output/ 2>/dev/null | grep -E '^[0-9]{8}_[0-9]{6}$' | sort -r | head -10
    else
        print_warning "No events output directory found"
    fi
    echo
    read -p "Enter timestamp (YYYYMMDD_HHMMSS): " TIMESTAMP
    if [ -z "$TIMESTAMP" ]; then
        print_error "Timestamp cannot be empty"
        exit 1
    fi
else
    TIMESTAMP=$1
    shift 1
fi

# Validate function
case $FUNCTION in
    review|merge|upload|cleanup)
        ;;
    *)
        print_error "Invalid function: $FUNCTION"
        show_usage
        exit 1
        ;;
esac

# Check if timestamp directory exists
TIMESTAMP_DIR="data/events_output/$TIMESTAMP"
if [ ! -d "$TIMESTAMP_DIR" ]; then
    print_warning "Timestamp directory does not exist: $TIMESTAMP_DIR"
    print_info "Make sure you have run the main process first"
fi

# Activate virtual environment and run the function
print_info "Activating virtual environment..."
source venv_main/bin/activate 2>/dev/null || source venv_main/Scripts/activate 2>/dev/null || {
    print_error "Could not activate virtual environment venv_main"
    print_info "Trying without virtual environment..."
}

print_info "Running function: $FUNCTION with timestamp: $TIMESTAMP"
python run_individual_functions.py $FUNCTION --timestamp $TIMESTAMP "$@"

# Check exit code
if [ $? -eq 0 ]; then
    print_success "Function $FUNCTION completed successfully"
else
    print_error "Function $FUNCTION failed"
    exit 1
fi 