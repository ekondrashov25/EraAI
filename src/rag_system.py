import logging
import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_core.documents import Document

from src.config import config

logger = logging.getLogger(__name__)

class RAGSystem:
    """Retrieval-Augmented Generation system using ChromaDB and LangChain."""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(api_key=config.OPENAI_API_KEY)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        # Initialize ChromaDB
        os.makedirs(config.CHROMA_DB_PATH, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(
            path=config.CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize vector store
        self.vectorstore = Chroma(
            client=self.chroma_client,
            collection_name="documents",
            embedding_function=self.embeddings
        )
    
    async def add_documents(
        self,
        documents: List[Document],
        collection_name: str = "documents"
    ) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of LangChain Document objects
            collection_name: Name of the collection to store documents
        """
        try:
            # Split documents into chunks
            texts = self.text_splitter.split_documents(documents)
            
            # Add to vector store
            self.vectorstore.add_documents(texts)
            
            logger.info(f"Added {len(texts)} document chunks to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            raise
    
    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Add raw texts to the vector store.
        
        Args:
            texts: List of text strings
            metadatas: Optional list of metadata dictionaries
        """
        try:
            # Split texts into chunks
            split_texts = []
            for text in texts:
                split_texts.extend(self.text_splitter.split_text(text))
            
            # Add to vector store
            self.vectorstore.add_texts(split_texts, metadatas=metadatas)
            
            logger.info(f"Added {len(split_texts)} text chunks to vector store")
            
        except Exception as e:
            logger.error(f"Error adding texts: {str(e)}")
            raise
    
    async def search_similar(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Search for similar documents in the vector store.
        
        Args:
            query: Search query
            k: Number of results to return
            filter_dict: Optional filter criteria
            
        Returns:
            List of similar documents
        """
        try:
            results = self.vectorstore.similarity_search(
                query,
                k=k,
                filter=filter_dict
            )
            
            logger.info(f"Found {len(results)} similar documents for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            raise
    
    async def search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[tuple[Document, float]]:
        """
        Search for similar documents with similarity scores.
        
        Args:
            query: Search query
            k: Number of results to return
            filter_dict: Optional filter criteria
            
        Returns:
            List of tuples containing (document, score)
        """
        try:
            results = self.vectorstore.similarity_search_with_score(
                query,
                k=k,
                filter=filter_dict
            )
            
            logger.info(f"Found {len(results)} similar documents with scores for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents with scores: {str(e)}")
            raise
    
    async def get_relevant_context(
        self,
        query: str,
        k: int = 3
    ) -> str:
        """
        Get relevant context for a query to use in RAG.
        
        Args:
            query: User query
            k: Number of documents to retrieve
            
        Returns:
            Formatted context string
        """
        try:
            documents = await self.search_similar(query, k=k)
            
            if not documents:
                return ""
            
            context_parts = []
            for i, doc in enumerate(documents, 1):
                context_parts.append(f"Document {i}:\n{doc.page_content}")
            
            context = "\n\n".join(context_parts)
            # Hard cap context size to avoid prompt bloat
            if len(context) > config.RAG_CONTEXT_MAX_CHARS:
                context = context[:config.RAG_CONTEXT_MAX_CHARS]
            logger.info(f"Retrieved context with {len(documents)} documents")
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting relevant context: {str(e)}")
            return ""
    
    async def load_documents_from_directory(
        self,
        directory_path: str,
        glob_pattern: str = "**/*.txt"
    ) -> None:
        """
        Load documents from a directory.
        
        Args:
            directory_path: Path to directory containing documents
            glob_pattern: Pattern to match files
        """
        try:
            loader = DirectoryLoader(
                directory_path,
                glob=glob_pattern,
                loader_cls=TextLoader
            )
            documents = loader.load()
            
            await self.add_documents(documents)
            
            logger.info(f"Loaded {len(documents)} documents from {directory_path}")
            
        except Exception as e:
            logger.error(f"Error loading documents from directory: {str(e)}")
            raise
    
    async def delete_collection(self, collection_name: str = "documents") -> None:
        """
        Delete a collection from the vector store.
        
        Args:
            collection_name: Name of the collection to delete
        """
        try:
            self.chroma_client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            collection = self.chroma_client.get_collection("documents")
            count = collection.count()
            
            return {
                "total_documents": count,
                "collection_name": "documents",
                "embedding_dimension": 1536  # OpenAI embeddings dimension
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {"error": str(e)}
