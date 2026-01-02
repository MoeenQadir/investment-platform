# Fix for Installation Errors

## Problem
You're using Python 3.14, which is not compatible with pandas 2.1.4. The installation fails when trying to build pandas.

## Solution

**Option 1: Use the setup script (Recommended)**
```bash
cd apps/api
./setup.sh
```

**Option 2: Manual fix**
```bash
cd apps/api

# Remove old venv
rm -rf venv

# Create venv with Python 3.11 (or 3.12)
python3.11 -m venv venv

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Now run migrations
alembic upgrade head
python scripts/seed_data.py
```

## If Python 3.11 is not installed

Install it with Homebrew:
```bash
brew install python@3.11
```

Then use `python3.11` instead of `python3` when creating the virtual environment.

