#!/usr/bin/env python3
"""
Test script to verify the frontend and API integration.
"""

import asyncio
import requests
import json
import time
import sys
import os

def test_api_connection():
    """Test if the API is running and responding."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is running: {data}")
            return True
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure simple_web_api.py is running on port 8000")
        return False
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False

def test_chat_functionality():
    """Test the chat functionality."""
    try:
        response = requests.post("http://localhost:8000/chat", 
                               json={"message": "Hello! How are you?", "use_rag": False, "use_functions": False},
                               timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and "content" in data["result"]:
                print("✅ Chat functionality working!")
                print(f"Response: {data['result']['content'][0]['text'][:100]}...")
                return True
            else:
                print(f"❌ Unexpected response format: {data}")
                return False
        else:
            print(f"❌ Chat request failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing chat: {e}")
        return False

def test_knowledge_functionality():
    """Test adding and searching knowledge."""
    try:
        # Test adding knowledge
        add_response = requests.post("http://localhost:8000/add_knowledge", 
                                   json={"texts": ["This is a test document about AI assistants."]},
                                   timeout=10)
        
        if add_response.status_code == 200:
            print("✅ Knowledge addition working!")
            
            # Test searching knowledge
            search_response = requests.get("http://localhost:8000/search?query=AI assistants", timeout=10)
            
            if search_response.status_code == 200:
                print("✅ Knowledge search working!")
                return True
            else:
                print(f"❌ Search failed with status: {search_response.status_code}")
                return False
        else:
            print(f"❌ Knowledge addition failed with status: {add_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing knowledge functionality: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Testing MCP AI Assistant Frontend Integration")
    print("=" * 60)
    
    # Test 1: API Connection
    print("\n1️⃣ Testing API Connection...")
    if not test_api_connection():
        print("\n❌ API test failed. Please start the API server first:")
        print("   python simple_web_api.py")
        return False
    
    # Test 2: Chat Functionality
    print("\n2️⃣ Testing Chat Functionality...")
    if not test_chat_functionality():
        print("\n❌ Chat test failed.")
        return False
    
    # Test 3: Knowledge Functionality
    print("\n3️⃣ Testing Knowledge Functionality...")
    if not test_knowledge_functionality():
        print("\n❌ Knowledge test failed.")
        return False
    
    print("\n🎉 All tests passed!")
    print("\n📋 Next steps:")
    print("1. Start the frontend server: python serve_frontend.py")
    print("2. Open http://localhost:3000 in your browser")
    print("3. Start chatting with your AI assistant!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
