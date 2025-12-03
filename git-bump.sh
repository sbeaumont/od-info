#!/bin/bash
# Bump the minor version and create a new git tag

latest=$(git tag --sort=-v:refname | head -1)
if [ -z "$latest" ]; then
    echo "No existing tags found"
    exit 1
fi

prefix=${latest%.*}
minor=${latest##*.}
next="$prefix.$((minor + 1))"

echo "Current: $latest"
echo "Next:    $next"
read -p "Create tag? [y/N] " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    git tag "$next"
    echo "Created tag $next"
else
    echo "Cancelled"
fi