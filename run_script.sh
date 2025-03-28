#!/bin/bash
set -e 
# improved_run_script.sh - Cross-platform Python dependency installer and XDP converter runner

# Hard-coded requirements file
REQUIREMENTS_FILE="requirements.txt"
VENV_DIR=".venv"

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

# Get Python and pip commands
PYTHON_CMD=$(get_python_command)
# PIP_CMD=$(get_pip_command)

# Check if Python 3 is available
if [ -z "$PYTHON_CMD" ]; then
    echo "Error: Python 3 is required but not found. Please install Python 3."
    exit 1
fi

echo "Using Python command: $PYTHON_CMD"

# Ensure venv module is available
if ! $PYTHON_CMD -m venv --help > /dev/null 2>&1; then
    echo "python3-venv is not installed. Attempting to install..."
    if command -v apt-get &> /dev/null; then
        if command -v sudo &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y python3-venv
        else
            echo "Error: 'sudo' not available. Please install 'python3-venv' manually."
            exit 1
        fi
    else
        echo "Unsupported system. Please install 'python3-venv' manually."
        exit 1
    fi
fi

# Create virtual environment if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "Attempting to create virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR" || echo "venv creation command failed"
fi

# Check if venv was created properly
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "Virtual environment not set up correctly (missing bin/activate)."
    echo ""

    if command -v apt-get &> /dev/null; then
        if command -v sudo &> /dev/null; then
            echo "Attempting to install 'python3-venv' using sudo..."
            sudo apt-get update && sudo apt-get install -y python3-venv
        elif [ "$(id -u)" -eq 0 ]; then
            echo "Running as root — installing 'python3-venv' directly..."
            apt-get update && apt-get install -y python3-venv
        else
            echo "sudo' is not available and you're not root."
            echo "Please install 'python3-venv' manually using:"
            echo "   apt-get install python3-venv"
            exit 1
        fi

        echo "Retrying virtual environment creation..."
        $PYTHON_CMD -m venv "$VENV_DIR"
    else
        echo "This system does not support apt-get. Please install 'python3-venv' manually."
        exit 1
    fi

    # Final check
    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        echo "Still failed to create virtual environment after installing python3-venv."
        exit 1
    fi
fi

# Activate virtualenv
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

PYTHON_CMD="$VENV_DIR/bin/python"
PIP_CMD="$VENV_DIR/bin/pip"


# Install dependencies
echo "Installing Python dependencies using $PIP_CMD..."
if [[ "$PIP_CMD" == *"-m pip" ]]; then
    # Using Python module format
    $PIP_CMD install -r "$REQUIREMENTS_FILE" > /dev/null 2>&1
else
    # Using standalone pip command
    $PIP_CMD install -r "$REQUIREMENTS_FILE" > /dev/null 2>&1
fi

# Check if installation was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies."
    exit 1
fi

echo "Dependency installation completed!"

# Run the XDP converter
echo "Starting XDP converter using $PYTHON_CMD..."
$PYTHON_CMD src/xdp_converter_cli.py "$@"