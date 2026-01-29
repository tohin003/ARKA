---
name: computer_forensics
description: "Analyze file systems, recovering metadata, and investigating disk usage."
---

# Computer Forensics Skill

## Overview
Use this skill to investigate the file system state, understand disk usage, and inspect file metadata securely.

## Tools

### `analyze_disk_usage(path: str)`
Recursively calculates disk usage for a directory and returns a sorted summary of top consumers.
-   Useful for "Why is my disk full?" queries.

### `get_detailed_metadata(path: str)`
Returns comprehensive metadata including access times, permissions, and extended attributes (where supported).
