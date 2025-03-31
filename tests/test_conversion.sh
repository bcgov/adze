#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Starting XML to JSON conversion test..."

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed. Please install jq first."
    exit 1
fi

# Clear output directory
echo "Clearing output directory..."
rm -rf data/output/*

# Run the CLI tool in batch mode
echo "Running XML to JSON conversion..."
PYTHONPATH="$PROJECT_ROOT/src" python3 -m xdp_converter_cli --input-dir data/input --output-dir data/output

# Compare outputs with reference files
echo "Comparing outputs with reference files..."
failed_tests=0

for output_file in data/output/*.json; do
    if [ -f "$output_file" ]; then
        # Extract the form ID from the output filename (everything before _output_)
        filename=$(basename "$output_file")
        form_id="${filename%%_output_*}"
        reference_file="data/reference/${form_id}.json"
        
        if [ -f "$reference_file" ]; then
            # Create temporary files without lastModified field
            output_temp=$(mktemp)
            reference_temp=$(mktemp)
            
            # Remove lastModified field from both files for comparison
            jq 'del(.. | .lastModified?)' "$output_file" > "$output_temp"
            jq 'del(.. | .lastModified?)' "$reference_file" > "$reference_temp"
            
            if diff "$output_temp" "$reference_temp" > /dev/null; then
                echo -e "${GREEN}✓ ${form_id} matches reference${NC}"
            else
                echo -e "${RED}✗ ${form_id} differs from reference${NC}"
                failed_tests=$((failed_tests + 1))
            fi
            
            # Clean up temporary files
            rm "$output_temp" "$reference_temp"
        else
            echo -e "${RED}✗ Reference file not found for ${form_id}${NC}"
            failed_tests=$((failed_tests + 1))
        fi
    fi
done

# Print summary
echo -e "\nTest Summary:"
if [ $failed_tests -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}$failed_tests test(s) failed${NC}"
    exit 1
fi 