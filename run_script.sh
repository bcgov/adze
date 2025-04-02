#!/bin/bash
set -e
cd "$(dirname "$0")"
# improved_run_script.sh - Cross-platform Python dependency installer and XDP converter runner

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

# Function to determine pip command
get_pip_command() {
    if command -v pip3 &> /dev/null; then
        echo "pip3"
    elif command -v pip &> /dev/null; then
        # Check if this is pip for Python 3
        PIP_VERSION=$(pip --version 2>&1)
        if [[ $PIP_VERSION == *"python 3"* ]] || [[ $PIP_VERSION == *"python3"* ]]; then
            echo "pip"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Get Python and pip commands
PYTHON_CMD=$(get_python_command)
PIP_CMD=$(get_pip_command)

# Check if Python 3 is available
if [ -z "$PYTHON_CMD" ]; then
    echo "Error: Python 3 is required but not found. Please install Python 3."
    exit 1
fi

echo "Using Python command: $PYTHON_CMD"

# Check if requirements file exists
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "Error: Requirements file 'requirements.txt' not found."
    echo "Please create a requirements.txt file in the current directory."
    exit 1
fi

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "Detected Linux OS"
    
    # Check if pip is installed
    if [ -z "$PIP_CMD" ]; then
        echo "Installing pip for Python 3..."
        sudo apt-get update
        sudo apt-get install -y python3-pip
        PIP_CMD="pip3"
    fi
    
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # Mac OS
    echo "Detected macOS"
    
    # Check if pip is installed
    if [ -z "$PIP_CMD" ]; then
        echo "Installing pip for Python 3..."
        # Check if Homebrew is installed
        if ! command -v brew &> /dev/null; then
            echo "Homebrew not found. Install Homebrew and then run the script again."
            exit 1
        fi
        brew install python3
        PIP_CMD="pip3"
    fi
    
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    echo "Detected Windows OS"
    
    # Windows detection for PowerShell
    if command -v powershell.exe &> /dev/null; then
        # Using PowerShell
        echo "Using PowerShell..."
        
        # Check for Python and pip
        if [ -z "$PYTHON_CMD" ]; then
            if command -v py &> /dev/null; then
                PYTHON_CMD="py"
                echo "Using Python Launcher (py)"
            else
                echo "Python 3 not found. Please install Python from https://www.python.org/downloads/"
                echo "Make sure to check 'Add Python to PATH' during installation."
                exit 1
            fi
        fi
        
        # Check for pip
        if [ -z "$PIP_CMD" ]; then
            echo "Installing pip..."
            $PYTHON_CMD -m ensurepip --upgrade
            PIP_CMD="$PYTHON_CMD -m pip"
        fi
    else
        # Fallback to regular command prompt
        echo "Using Command Prompt..."
        
        if [ -z "$PIP_CMD" ]; then
            if [ -n "$PYTHON_CMD" ]; then
                echo "Installing pip..."
                $PYTHON_CMD -m ensurepip --upgrade
                PIP_CMD="$PYTHON_CMD -m pip"
            else
                echo "Python/pip not found. Please install Python from https://www.python.org/downloads/"
                echo "Make sure to check 'Add Python to PATH' during installation."
                exit 1
            fi
        fi
    fi
else
    # Unknown OS
    echo "Unknown operating system: $OSTYPE"
    echo "Proceeding with detected Python/pip commands..."
    
    if [ -z "$PIP_CMD" ] && [ -n "$PYTHON_CMD" ]; then
        echo "Attempting to install pip..."
        $PYTHON_CMD -m ensurepip --upgrade
        PIP_CMD="$PYTHON_CMD -m pip"
    fi
    
    if [ -z "$PIP_CMD" ]; then
        echo "Error: pip not found and cannot be installed automatically."
        echo "Please install pip manually or use: $PYTHON_CMD -m pip"
        exit 1
    fi
fi

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