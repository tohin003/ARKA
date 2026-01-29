---
name: file_organizer
description: "Automatically organize cluttered directories by file type or date."
---

# File Organizer Skill

## Overview
Use this skill to clean up messy folders (like Downloads or Desktop).

## Tools

### `organize_directory(path: str, strategy: str)`
Moves files into subfolders based on the chosen strategy.
-   `extension`: Sorts into `Images/`, `Documents/`, `Archives/`, etc.
-   `date`: Sorts into `YYYY/MM/`.
-   `keyword`: Uses LLM-inferred relevance if provided (not yet implemented, stick to ext/date).

## Best Practices
-   Always `analyze_disk_usage` or `ls` first to see what you are organizing.
-   Ask for confirmation before organizing critical system folders.
