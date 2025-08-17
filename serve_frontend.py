import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

def main():
    frontend_dir = Path(__file__).parent / "frontend"
    os.chdir(frontend_dir)
    
    PORT = 3000
    
    Handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🌐 Frontend server started at http://localhost:{PORT}")
        print(f"📁 Serving files from: {frontend_dir}")
        print()
        print("📋 To test the MCP AI Assistant:")
        print("1. Start the API server: python simple_web_api.py")
        print("2. Open this URL in your browser: http://localhost:3000")
        print("3. Start chatting with your AI assistant!")
        print()
        print("Press Ctrl+C to stop the server")
        
        # Open browser automatically
        try:
            webbrowser.open(f"http://localhost:{PORT}")
        except:
            pass
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")

if __name__ == "__main__":
    main()
