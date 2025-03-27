#!/bin/bash
# Entry script for running the XDP converter in OpenShift

# Hard-coded requirements file
REQUIREMENTS_FILE="requirements.txt"

# Function to determine Python command
get_python_command() {
    if command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        # Check if this is Python 3
        PYTHON_VERSION=$(python --version 2>&1)
        if [[ $PYTHON_VERSION == *"Python 3"* ]]; then
            echo "python"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Get Python command
PYTHON_CMD=$(get_python_command)

# Check if Python 3 is available
if [ -z "$PYTHON_CMD" ]; then
    echo "Error: Python 3 is required but not found. Please install Python 3 at build time."
    exit 1
fi

echo "Using Python command: $PYTHON_CMD"

# Check if requirements file exists
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "Error: Requirements file 'requirements.txt' not found."
    exit 1
fi

# Install dependencies (ONLY if not already installed, avoids OpenShift issues)
echo "Checking dependencies..."
$PYTHON_CMD -m pip install --no-cache-dir -r "$REQUIREMENTS_FILE"

if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies."
    exit 1
fi

echo "Dependencies installed successfully!"

# Run the XDP converter
echo "Starting XDP converter using $PYTHON_CMD..."
exec $PYTHON_CMD src/xdp_converter_cli.py "$@"
