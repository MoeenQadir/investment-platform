#!/bin/bash
# Setup script for API backend
# This script sets up the Python environment with the correct Python version

set -e

echo "Setting up API backend..."

# Check for Python 3.11 or 3.12
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD=python3.11
    echo "Using Python 3.11"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD=python3.12
    echo "Using Python 3.12"
elif command -v python3.13 &> /dev/null; then
    PYTHON_CMD=python3.13
    echo "Using Python 3.13"
else
    echo "ERROR: Python 3.11, 3.12, or 3.13 is required"
    echo "Current Python version: $(python3 --version)"
    echo "Please install Python 3.11-3.13 using: brew install python@3.11"
    exit 1
fi

# Remove old venv if it exists
if [ -d "venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf venv
fi

# Create virtual environment with correct Python version
echo "Creating virtual environment..."
$PYTHON_CMD -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setup complete! To activate the environment, run:"
echo "  source venv/bin/activate"

