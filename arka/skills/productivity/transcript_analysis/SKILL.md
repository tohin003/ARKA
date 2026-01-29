---
name: transcript_analysis
description: "Expertly analyze meeting transcripts, extract action items, and summarize discussions."
---

# Meeting & Transcript Analysis

## Overview
This skill provides specific prompts and strategies for handling transcript files (VTT, SRT, or raw text).

## Strategy
When asked to analyze a transcript:
1.  **Read** the file using `read_file`.
2.  **Identify** speakers and timestamps using regex or string splitting.
3.  **Synthesize** the conversation using the following structure:

### Output Template
```markdown
# [Meeting Title/Subject] Summary

## Executive Summary
(3-4 sentences capturing the main outcome)

## Key Decisions
- [Decision 1]
- [Decision 2]

## Action Items
- [ ] @Person: Task (Context)
- [ ] @Person: Task (Context)

## Detailed Notes
(Structured by topic, not chronological order)
```

## Tips
-   Ignore filler words ("um", "uh").
-   Consolidate fragmented sentences.
-   If meaningful timestamps are present, link to them in the output.
