# Advanced MCP Backend Server - Quick Start Guide

## 🎯 Get Started in 5 Minutes

### Step 1: Install Python Dependencies

**Option A: Using uv (Recommended - Faster)**
```bash
cd c:\Users\VYSHNAVI R\OneDrive\MCP
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

**Option B: Using pip**
```bash
cd c:\Users\VYSHNAVI R\OneDrive\MCP
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Start the Server

```bash
# Make sure you're in the activated virtual environment
python src/server.py
```

You should see:
```
Starting Advanced MCP Server...
```

### Step 3: Test the Server (Optional)

In a **new terminal** with the virtual environment activated:

```bash
python test_client.py
```

This will:
✓ Connect to your server
✓ Test all available tools
✓ Display available resources and prompts
✓ Show example results

---

## 📱 Integration with VS Code

### Configuration
The server is already configured in `.vscode/mcp.json`:

```json
{
  "servers": {
    "advanced-mcp-server": {
      "type": "stdio",
      "command": "python",
      "args": ["${workspaceFolder}/src/server.py"]
    }
  }
}
```

### Using with Claude Desktop
1. Copy the server configuration to Claude Desktop's config
2. Restart Claude Desktop
3. The server tools will be available in the conversation

### Using with Other MCP Clients
Update your client configuration to point to:
```
command: python
args: [path/to/src/server.py]
```

---

## 🔧 Configuration

Edit `.env` to customize behavior:

```env
# API Settings
API_TIMEOUT=30              # Timeout in seconds
API_MAX_RETRIES=3          # Number of retries for failed requests

# Server Settings
LOG_LEVEL=INFO             # DEBUG, INFO, WARNING, ERROR
DEBUG_MODE=false           # Enable debug logging

# Performance
MAX_WORKERS=4              # Number of worker threads
MEMORY_LIMIT_MB=512        # Memory limit
```

---

## 📚 Using the Tools

### Example 1: Analyze Text
```python
# In any MCP client:
tool: analyze_text
parameters:
  text: "This is amazing code with great features!"
  analyze_sentiment: true
  extract_keywords: true

# Returns sentiment analysis and keywords
```

### Example 2: Process Large Data
```python
tool: process_data
parameters:
  data_size: 5000
  operation: transform

# Shows progress as it processes
```

### Example 3: Analyze Code
```python
tool: analyze_code
parameters:
  code: "(your code here)"
  language: python

# Returns complexity metrics and structure analysis
```

### Example 4: Call an API
```python
tool: fetch_data_from_api
parameters:
  url: https://api.example.com/data
  method: GET
  timeout: 30

# Fetches and returns the API response
```

### Example 5: Execute Database Query
```python
tool: execute_database_query
parameters:
  query: SELECT * FROM users
  transaction: false

# Returns query results and metrics
```

---

## 🚀 Advanced Features

### Progress Tracking
Long-running operations (like `process_data`) provide real-time progress updates:
- Progress percentage
- Current operation message
- Estimated completion time

### Structured Output
All tools return properly typed, validated responses:
- Type safety with Pydantic models
- Automatic JSON serialization
- Schema validation

### Error Handling
Comprehensive error handling:
- Timeout protection
- Network error recovery
- Detailed error messages
- Automatic logging

### Resources
Access dynamic data via resource URIs:

```
config://settings/api          # API configuration
config://settings/features     # Feature flags
config://settings/system       # System settings
stats://metrics               # Server statistics
```

---

## 🔍 Debugging

### Enable Debug Mode
```env
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

### View Server Logs
Logs are printed to console. Look for:
- `[INFO]` - Normal operations
- `[DEBUG]` - Detailed information
- `[WARNING]` - Potential issues
- `[ERROR]` - Errors that occurred

### Test Individual Tool
```bash
python test_client.py
```

---

## ⚡ Performance Tips

1. **Data Processing**: Use appropriate `data_size` for your use case
2. **API Calls**: Increase `API_TIMEOUT` for slow APIs
3. **Concurrency**: Adjust `MAX_WORKERS` based on your system
4. **Memory**: Monitor `MEMORY_LIMIT_MB` for large operations

---

## 🐛 Troubleshooting

### "ImportError: No module named 'mcp'"
```bash
# Make sure virtual environment is activated
.venv\Scripts\activate
# Then reinstall dependencies
pip install -r requirements.txt
```

### "Connection refused"
- Ensure server is running: `python src/server.py`
- Check port configuration in `.vscode/mcp.json`
- Verify firewall settings

### Server exits immediately
1. Check `.env` file exists
2. Look for error messages in console
3. Verify Python version: `python --version` (should be 3.10+)

### Tools not appearing in client
1. Restart your MCP client
2. Verify server started without errors
3. Check `.vscode/mcp.json` configuration
4. Try running `test_client.py` first

---

## 📦 What's Included

- ✅ 5 production-ready tools
- ✅ 2 dynamic resources
- ✅ 2 interactive prompts
- ✅ Full async/await support
- ✅ Comprehensive error handling
- ✅ Progress tracking
- ✅ Structured output types
- ✅ Environment configuration
- ✅ Test client
- ✅ Full documentation

---

## 🎓 Next Steps

1. **Explore the Code**: Open `src/server.py` to see implementation
2. **Add Custom Tools**: Extend with your own tools
3. **Customize Configuration**: Update `.env` for your needs
4. **Integrate with Apps**: Use with Claude Desktop or your MCP client
5. **Deploy**: Ready for production deployment

---

## 📖 Resources

- [MCP Specification](https://modelcontextprotocol.io/)
- [Python SDK Docs](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP Guide](https://modelcontextprotocol.github.io/python-sdk/)

---

## ✨ Features at a Glance

| Feature | Status | Description |
|---------|--------|-------------|
| Text Analysis | ✅ | Sentiment, keywords, readability |
| Code Analysis | ✅ | Complexity, structure, metrics |
| API Integration | ✅ | REST API calls with error handling |
| Data Processing | ✅ | Large-scale data with progress |
| Database Ops | ✅ | SQL execution and transactions |
| Progress Tracking | ✅ | Real-time operation updates |
| Error Handling | ✅ | Robust exception management |
| Logging | ✅ | Professional logging system |
| Structured Output | ✅ | Type-safe responses |
| Async/Await | ✅ | Non-blocking operations |

---

**Status**: Ready to Use ✅  
**Version**: 1.0.0  
**Last Updated**: December 2024
