---
name: file_integrity
description: "Securely delete files to prevent recovery."
---

# File Integrity Skill

## Overview
Standard deletion (`rm`) only removes the reference to the file. This skill provides tools to **securely delete** files by overwriting their content before removal.

## Tools

### `secure_delete_file(path: str, passes: int = 1)`
Securely deletes a file.
1.  Overwrites content with random bytes (for `passes` iterations).
2.  Overwrites with zeros.
3.  Renames the file to a random string (to obscure filename).
4.  Deletes the file.

> [!WARNING]
> This action is **IRREVERSIBLE**. Use with extreme caution.
