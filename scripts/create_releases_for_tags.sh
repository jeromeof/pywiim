#!/bin/bash
# Helper script to create GitHub releases for existing tags that don't have releases
# Usage: ./scripts/create_releases_for_tags.sh [tag1] [tag2] ...
# If no tags provided, will create releases for all tags that don't have releases yet

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    error "GitHub CLI (gh) is not installed."
    error "Install it from: https://cli.github.com/"
    error "Then authenticate with: gh auth login"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    error "Not authenticated with GitHub CLI."
    error "Run: gh auth login"
    exit 1
fi

# Function to extract changelog entry for a version
extract_changelog() {
    local version=$1
    local changelog_file="CHANGELOG.md"
    
    if [ ! -f "$changelog_file" ]; then
        return 1
    fi
    
    # Find the section for this version (e.g., "## [1.0.25]")
    local start_line=$(grep -n "^## \[$version\]" "$changelog_file" | cut -d: -f1)
    
    if [ -z "$start_line" ]; then
        return 1
    fi
    
    # Find the next version section or end of file
    local end_line=$(awk -v start="$start_line" 'NR > start && /^## \[/ {print NR-1; exit}' "$changelog_file")
    
    if [ -z "$end_line" ]; then
        # No next version found, read to end of file (but skip the link references at the bottom)
        end_line=$(grep -n "^\[Unreleased\]:" "$changelog_file" | cut -d: -f1)
        if [ -z "$end_line" ]; then
            end_line=$(wc -l < "$changelog_file")
        else
            end_line=$((end_line - 1))
        fi
    fi
    
    # Extract the changelog section (skip the version header line, keep content)
    sed -n "$((start_line + 1)),${end_line}p" "$changelog_file"
}

# Function to check if a release already exists for a tag
release_exists() {
    local tag=$1
    gh release view "$tag" &> /dev/null
}

# Function to create release for a tag
create_release() {
    local tag=$1
    local version=${tag#v}  # Remove 'v' prefix if present
    
    step "Processing tag: $tag"
    
    # Check if release already exists
    if release_exists "$tag"; then
        warn "Release for $tag already exists, skipping"
        return 0
    fi
    
    # Extract changelog
    CHANGELOG_NOTES=$(extract_changelog "$version")
    
    if [ -n "$CHANGELOG_NOTES" ]; then
        info "Creating release $tag with changelog notes..."
        echo "$CHANGELOG_NOTES" | gh release create "$tag" \
            --title "Release $tag" \
            --notes-file - \
            --target main
        info "✓ Release created for $tag"
    else
        warn "No changelog found for version $version, creating release without notes"
        gh release create "$tag" \
            --title "Release $tag" \
            --notes "Release $tag" \
            --target main
        info "✓ Release created for $tag (without changelog)"
    fi
}

# Main logic
if [ $# -eq 0 ]; then
    # No tags provided, find all tags and create releases for those without releases
    info "No tags specified. Finding all tags and creating releases for those without releases..."
    
    # Get all tags
    TAGS=$(git tag --list | sort -V)
    
    if [ -z "$TAGS" ]; then
        warn "No tags found in repository"
        exit 0
    fi
    
    info "Found $(echo "$TAGS" | wc -l) tags"
    
    for tag in $TAGS; do
        if ! release_exists "$tag"; then
            create_release "$tag"
            echo ""  # Blank line for readability
        else
            info "Release for $tag already exists, skipping"
        fi
    done
else
    # Process specified tags
    for tag in "$@"; do
        # Remove 'v' prefix if user didn't include it
        if [[ ! "$tag" =~ ^v ]]; then
            tag="v$tag"
        fi
        
        # Verify tag exists
        if ! git rev-parse "$tag" &> /dev/null; then
            error "Tag $tag does not exist"
            continue
        fi
        
        create_release "$tag"
        echo ""  # Blank line for readability
    done
fi

info "Done!"

