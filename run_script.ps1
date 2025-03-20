# improved_run_script.ps1 - PowerShell script for Python dependency installation and XDP converter running

# Hard-coded requirements file
$RequirementsFile = "requirements.txt"

# Function to determine Python command
function Get-PythonCommand {
    # Check for Python commands in this order of preference
    $commands = @("py", "python3", "python")
    
    foreach ($cmd in $commands) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            # Verify it's Python 3
            $versionOutput = & $cmd --version 2>&1
            if ($versionOutput -match "Python 3") {
                return $cmd
            }
        }
    }
    
    return $null
}

# Function to determine pip command
function Get-PipCommand {
    # Check for pip or use python -m pip
    $pythonCmd = $args[0]
    
    # Try standalone pip commands first
    $commands = @("pip3", "pip")
    foreach ($cmd in $commands) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            # Verify it's for Python 3
            $versionOutput = & $cmd --version 2>&1
            if ($versionOutput -match "python 3" -or $versionOutput -match "python3") {
                return $cmd
            }
        }
    }
    
    # Fall back to module-based pip
    return "$pythonCmd -m pip"
}

# Check if requirements file exists
if (-not (Test-Path $RequirementsFile)) {
    Write-Host "Error: Requirements file 'requirements.txt' not found." -ForegroundColor Red
    Write-Host "Please create a requirements.txt file in the current directory." -ForegroundColor Yellow
    exit 1
}

# Get Python command
$PythonCmd = Get-PythonCommand
if (-not $PythonCmd) {
    Write-Host "Error: Python 3 is required but not found." -ForegroundColor Red
    Write-Host "Please install Python 3 from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    exit 1
}

Write-Host "Using Python command: $PythonCmd" -ForegroundColor Green

# Get pip command
$PipCmd = Get-PipCommand $PythonCmd
if ($PipCmd -match "-m pip") {
    Write-Host "Using module-based pip: $PipCmd" -ForegroundColor Cyan
} else {
    Write-Host "Using pip command: $PipCmd" -ForegroundColor Cyan
}

# Ensure pip is installed and up to date
if ($PipCmd -match "-m pip") {
    Write-Host "Ensuring pip is installed and up to date..." -ForegroundColor Cyan
    & $PythonCmd -m ensurepip --upgrade > $null
    & $PythonCmd -m pip install --upgrade pip > $null
}

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
try {
    # Hide output by redirecting to null
    $null = & Invoke-Expression "$PipCmd install -r $RequirementsFile" 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        throw "Pip installation returned error code: $LASTEXITCODE"
    }
    
    Write-Host "Dependency installation completed!" -ForegroundColor Green
}
catch {
    Write-Host "Error installing dependencies: $_" -ForegroundColor Red
    exit 1
}

# Run the XDP converter
Write-Host "Starting XDP converter using $PythonCmd..." -ForegroundColor Cyan
try {
    & $PythonCmd src/xdp_converter_cli.py $args
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "XDP converter exited with code: $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
catch {
    Write-Host "Error running XDP converter: $_" -ForegroundColor Red
    exit 1
}