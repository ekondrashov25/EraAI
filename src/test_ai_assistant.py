#!/usr/bin/env python3
"""
Test script for AI Assistant with function calling.
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_assistant import AIAssistant

async def test_ai_assistant():
    """Test AI Assistant with function calling."""
    assistant = AIAssistant()
    
    try:
        # Test with a question that should trigger function calling
        response = await assistant.chat(
            "What is the current price of Bitcoin?",
            use_rag=False,  # Disable RAG for this test
            use_functions=True
        )
        
        print("✅ AI Assistant Response:")
        print(response.get('response', 'No response'))
        
        if response.get('function_calls'):
            print(f"\n🔧 Function calls made: {len(response['function_calls'])}")
            for call in response['function_calls']:
                print(f"  - {call['function_name']}: {call['status']}")
        
        # Test with another question
        print("\n" + "="*50)
        response2 = await assistant.chat(
            "What is the market cap of Ethereum?",
            use_rag=False,
            use_functions=True
        )
        
        print("✅ Second Response:")
        print(response2.get('response', 'No response'))
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        await assistant.cleanup()

if __name__ == "__main__":
    asyncio.run(test_ai_assistant())
