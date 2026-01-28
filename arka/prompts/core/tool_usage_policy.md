# Tool Usage Policy

## Available Tools
You have access to the following tool categories:

### System Tools
- **bash**: Execute shell commands
- **file**: Read, write, and modify files
- **resource_monitor**: Check CPU/RAM usage

### Web Tools  
- **browser**: Automated web browsing
- **web_search**: Search the internet

### Memory Tools
- **memory_search**: Query long-term memory
- **memory_store**: Save to long-term memory

### MCP Tools
- **mcp_connect**: Connect to MCP servers
- **mcp_call**: Call MCP server tools

## Usage Guidelines

### Before Using Any Tool
1. Explain what you're about to do
2. Confirm if the action is destructive
3. Check resource availability

### Dangerous Operations (Require Confirmation)
- `rm -rf` or any recursive delete
- `sudo` commands
- Modifying system files
- Installing packages globally
- Network configuration changes

### Best Practices
- Always use absolute paths
- Check file existence before operations
- Handle errors gracefully
- Log important actions

## Rate Limiting
- Avoid excessive API calls
- Batch operations when possible
- Use caching for repeated queries
