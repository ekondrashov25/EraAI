#!/usr/bin/env python3
"""
Simple script to upload PDF files to the RAG system.
Run this once to populate your knowledge base with PDF documents.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_assistant import AIAssistant

async def upload_pdfs_from_directory(pdf_directory: str = "pdfs"):
    """Upload all PDF files from a directory to the RAG system."""
    
    # Create PDF directory if it doesn't exist
    pdf_path = Path(pdf_directory)
    if not pdf_path.exists():
        print(f"📁 Creating directory: {pdf_directory}")
        pdf_path.mkdir(exist_ok=True)
        print(f"📄 Please place your PDF files in the '{pdf_directory}' directory and run this script again.")
        return
    
    # Find all PDF files
    pdf_files = list(pdf_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"📄 No PDF files found in '{pdf_directory}' directory.")
        print(f"📁 Please place your PDF files in the '{pdf_directory}' directory and run this script again.")
        return
    
    print(f"🚀 Found {len(pdf_files)} PDF file(s) to upload:")
    for pdf_file in pdf_files:
        print(f"  📄 {pdf_file.name}")
    
    # Initialize AI Assistant
    print("\n🤖 Initializing AI Assistant...")
    assistant = AIAssistant()
    
    # Upload each PDF
    for pdf_file in pdf_files:
        print(f"\n📤 Uploading: {pdf_file.name}")
        try:
            with open(pdf_file, 'rb') as f:
                pdf_content = f.read()
            
            result = await assistant.add_pdf_content(pdf_content, pdf_file.name)
            
            if result["status"] == "success":
                print(f"✅ Successfully uploaded: {pdf_file.name}")
                print(f"   📊 {result.get('pages_processed', 0)} pages processed")
                print(f"   📝 {result.get('chunks_added', 0)} text chunks added")
            else:
                print(f"❌ Failed to upload: {pdf_file.name}")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error uploading {pdf_file.name}: {str(e)}")
    
    # Show final stats
    print("\n📊 Final RAG System Stats:")
    try:
        info = await assistant.get_system_info()
        print(f"   📚 Total documents: {info['rag_system']['total_documents']}")
        print(f"   🗂️  Collection: {info['rag_system']['collection_name']}")
    except Exception as e:
        print(f"   ❌ Could not get stats: {str(e)}")
    
    print("\n🎉 PDF upload complete!")

async def upload_single_pdf(pdf_path: str):
    """Upload a single PDF file to the RAG system."""
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    if not pdf_file.suffix.lower() == '.pdf':
        print(f"❌ File is not a PDF: {pdf_path}")
        return
    
    print(f"🚀 Uploading single PDF: {pdf_file.name}")
    
    # Initialize AI Assistant
    print("🤖 Initializing AI Assistant...")
    assistant = AIAssistant()
    
    try:
        with open(pdf_file, 'rb') as f:
            pdf_content = f.read()
        
        result = await assistant.add_pdf_content(pdf_content, pdf_file.name)
        
        if result["status"] == "success":
            print(f"✅ Successfully uploaded: {pdf_file.name}")
            print(f"   📊 {result.get('pages_processed', 0)} pages processed")
            print(f"   📝 {result.get('chunks_added', 0)} text chunks added")
        else:
            print(f"❌ Failed to upload: {pdf_file.name}")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error uploading {pdf_file.name}: {str(e)}")

def main():
    """Main function to handle command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload PDF files to the RAG system")
    parser.add_argument("--directory", "-d", default="pdfs", 
                       help="Directory containing PDF files (default: pdfs)")
    parser.add_argument("--file", "-f", 
                       help="Single PDF file to upload")
    
    args = parser.parse_args()
    
    if args.file:
        # Upload single file
        asyncio.run(upload_single_pdf(args.file))
    else:
        # Upload all PDFs from directory
        asyncio.run(upload_pdfs_from_directory(args.directory))

if __name__ == "__main__":
    main()
