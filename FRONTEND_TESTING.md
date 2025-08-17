# Frontend Testing Guide

## Quick Start

Test your MCP AI Assistant with a beautiful web interface!

### Step 1: Start the API Server

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Start the MCP AI Assistant API
python simple_web_api.py
```

You should see:
```
🌐 Starting MCP AI Assistant Web API...
📖 API Documentation: http://localhost:8000/docs
🔗 Health Check: http://localhost:8000/health
```

### Step 2: Start the Frontend Server

In a new terminal:

```bash
# Start the frontend server
python serve_frontend.py
```

You should see:
```
🌐 Frontend server started at http://localhost:3000
📁 Serving files from: /path/to/frontend
```

### Step 3: Test the Interface

1. Open your browser and go to: **http://localhost:3000**
2. You should see a beautiful chat interface
3. Start chatting with your AI assistant!

## Features

The frontend includes:

- 🤖 **Real-time Chat**: Send messages and get AI responses
- 📚 **Add Knowledge**: Add documents to the RAG system
- 🔍 **Search Knowledge**: Search through your knowledge base
- ℹ️ **System Info**: View system statistics
- 📜 **Conversation History**: View and manage chat history
- 🗑️ **Clear History**: Reset the conversation

## Testing the Integration

Run the test script to verify everything works:

```bash
python test_frontend.py
```

This will test:
- ✅ API connection
- ✅ Chat functionality
- ✅ Knowledge management

## API Endpoints

The frontend connects to these API endpoints:

- `POST /chat` - Send messages to the AI assistant
- `POST /add_knowledge` - Add documents to RAG
- `GET /search` - Search knowledge base
- `GET /system_info` - Get system information
- `GET /conversation_history` - Get chat history
- `POST /clear_history` - Clear conversation history

## Troubleshooting

### API Not Connecting
- Make sure `simple_web_api.py` is running on port 8000
- Check that your OpenAI API key is set in `.env`

### Frontend Not Loading
- Make sure `serve_frontend.py` is running on port 3000
- Check that the `frontend/` directory exists with `index.html`

### CORS Errors
- The API includes CORS middleware for local development
- For production, configure CORS appropriately

## Customization

You can customize the frontend by editing:
- `frontend/index.html` - Main interface
- `simple_web_api.py` - API endpoints
- CSS styles in the HTML file for visual changes

## Next Steps

Once you've tested the frontend:
1. Customize the interface for your needs
2. Add authentication if required
3. Deploy to production
4. Integrate with other applications

Happy testing! 🚀
