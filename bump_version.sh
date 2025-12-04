#!/bin/bash
# Script to manually bump version
# Usage: ./bump_version.sh [major|minor|patch]

VERSION_FILE="VERSION"
CURRENT_VERSION=$(cat $VERSION_FILE | tr -d '\n')

if [ -z "$CURRENT_VERSION" ]; then
    echo "Error: VERSION file is empty or doesn't exist"
    exit 1
fi

IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR=${VERSION_PARTS[0]}
MINOR=${VERSION_PARTS[1]}
PATCH=${VERSION_PARTS[2]}

BUMP_TYPE=${1:-patch}

case $BUMP_TYPE in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
    *)
        echo "Usage: $0 [major|minor|patch]"
        echo "Current version: $CURRENT_VERSION"
        exit 1
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"

echo "Current version: $CURRENT_VERSION"
echo "New version: $NEW_VERSION"
echo "$NEW_VERSION" > $VERSION_FILE

echo "Version bumped to $NEW_VERSION"
echo "Don't forget to commit: git add VERSION && git commit -m 'Bump version to $NEW_VERSION'"

