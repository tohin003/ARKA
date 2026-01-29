---
name: sql_analysis
description: "Execute safe, read-only SQL queries against a database to analyze data."
---

# SQL Analysis Skill

## Overview
This skill provides tools to inspect database schemas and run analytical queries. It is strictly **READ-ONLY** to prevent accidental data modification.

## Tools

### `execute_readonly_sql(connection_string: str, query: str)`
Executes a SQL query.
-   **Blocked Keywords**: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE.
-   **Returns**: Query results as a formatted string (or JSON).

## Usage
1.  Construct a valid SQLAlchemy connection string (e.g., `postgresql://user:pass@localhost:5432/db`).
2.  Write your SELECT query.
3.  Call the tool.

## Safety
This tool includes a safety layer that checks for destructive keywords. However, you should still be careful efficiently writing queries to avoid performance impact.
