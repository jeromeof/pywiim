#!/bin/bash
# Helper script to authenticate GitHub CLI with a Personal Access Token
# Usage: ./scripts/gh-auth-token.sh

set -e

echo "=== GitHub CLI Token Authentication ==="
echo ""
echo "This script will help you authenticate GitHub CLI with a PAT."
echo ""

# Check if token is provided as argument
if [ -n "$1" ]; then
    TOKEN="$1"
    echo "Token provided as argument. Authenticating..."
    echo "$TOKEN" | gh auth login --with-token
    echo ""
    echo "✅ Authentication successful!"
    gh auth status
elif [ -n "$GH_TOKEN" ]; then
    echo "GH_TOKEN environment variable found. Authenticating..."
    echo "$GH_TOKEN" | gh auth login --with-token
    echo ""
    echo "✅ Authentication successful!"
    gh auth status
else
    echo "No token provided. Please choose one of these methods:"
    echo ""
    echo "Method 1: Interactive (most secure)"
    echo "  Run: gh auth login --with-token"
    echo "  Then paste your token when prompted"
    echo ""
    echo "Method 2: Environment variable"
    echo "  export GH_TOKEN='your_token_here'"
    echo "  ./scripts/gh-auth-token.sh"
    echo ""
    echo "Method 3: Direct (less secure - token visible in command history)"
    echo "  ./scripts/gh-auth-token.sh 'your_token_here'"
    echo ""
    echo "Method 4: From file (secure)"
    echo "  echo 'your_token_here' > /tmp/gh_token.txt"
    echo "  cat /tmp/gh_token.txt | gh auth login --with-token"
    echo "  rm /tmp/gh_token.txt"
    echo ""
    echo "After authenticating, verify with: gh auth status"
fi

