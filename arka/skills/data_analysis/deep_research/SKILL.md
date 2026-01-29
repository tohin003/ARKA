---
name: deep_research
description: "Conduct comprehensive web research on a topic. Use this when the user needs a detailed summary, fact-checking, or background information that requires checking multiple sources."
---

# Deep Research Skill

## Overview
This skill allows you to perform in-depth research on a topic by automatically searching, visiting multiple pages, and extracting relevant content.

## Tools

### `perform_deep_research(query: str, max_depth: int = 3)`
Executes a multi-step research workflow:
1.  Searches Google for the `query`.
2.  Visits the top `max_depth` results (default 3).
3.  Extracts main content from each page.
4.  Returns a structured summary of findings.

## Best Practices
-   Use specific, targeted queries.
-   If the topic is broad, break it down into multiple `perform_deep_research` calls.
-   Always cite the source URLs provided in the output.
-   Be critical of the sources; the tool provides raw text, you must evaluate credibility.
