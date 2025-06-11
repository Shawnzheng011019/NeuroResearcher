import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, AsyncGenerator
from pathlib import Path
from datetime import datetime
import argparse

from .rag_document_processor import RAGDocumentProcessor
from .rag_retriever import RAGRetriever
from config import Config, get_config

logger = logging.getLogger(__name__)


class RAGManager:
    def __init__(self, config: Config):
        self.config = config
        self.processor = RAGDocumentProcessor(config)
        self.retriever = RAGRetriever(config)
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        try:
            # Initialize processor
            processor_success = await self.processor.initialize()
            if not processor_success:
                logger.error("Failed to initialize RAG processor")
                return False
            
            # Initialize retriever
            retriever_success = await self.retriever.initialize()
            if not retriever_success:
                logger.error("Failed to initialize RAG retriever")
                return False
            
            self.is_initialized = True
            logger.info("RAG Manager initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize RAG Manager: {str(e)}")
            return False
    
    async def index_documents(self, source_path: str, 
                            recursive: bool = True) -> Dict[str, Any]:
        if not self.is_initialized:
            raise RuntimeError("RAG Manager not initialized")
        
        source = Path(source_path)
        
        if source.is_file():
            # Process single file
            result = await self.processor.process_file(str(source))
            return {
                "type": "file",
                "source": str(source),
                "result": result
            }
        
        elif source.is_dir():
            # Process directory
            result = await self.processor.process_directory(str(source))
            return {
                "type": "directory",
                "source": str(source),
                "result": result
            }
        
        else:
            raise ValueError(f"Source path does not exist: {source_path}")
    
    async def search_documents(self, query: str, 
                             top_k: int = 10,
                             document_types: Optional[List[str]] = None,
                             source_filter: Optional[str] = None,
                             similarity_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        if not self.is_initialized:
            raise RuntimeError("RAG Manager not initialized")
        
        return await self.retriever.retrieve_relevant_documents(
            query=query,
            top_k=top_k,
            document_types=document_types,
            source_filter=source_filter,
            similarity_threshold=similarity_threshold
        )
    
    async def hybrid_search(self, query: str,
                          web_results: Optional[List[Dict[str, Any]]] = None,
                          local_weight: float = 0.7,
                          web_weight: float = 0.3,
                          max_results: int = 20) -> List[Dict[str, Any]]:
        if not self.is_initialized:
            raise RuntimeError("RAG Manager not initialized")
        
        return await self.retriever.hybrid_retrieve(
            query=query,
            web_results=web_results,
            local_weight=local_weight,
            web_weight=web_weight,
            max_total_results=max_results
        )
    
    async def get_document_types(self) -> List[str]:
        if not self.is_initialized:
            return []
        
        try:
            # This would require a specific query to get unique document types
            # For now, return the configured supported formats
            return self.config.supported_formats
        except Exception as e:
            logger.error(f"Failed to get document types: {str(e)}")
            return []
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        if not self.is_initialized:
            return {}
        
        return await self.retriever.get_stats()
    
    async def delete_documents_by_source(self, source_pattern: str) -> bool:
        if not self.is_initialized:
            raise RuntimeError("RAG Manager not initialized")
        
        try:
            # First, find documents matching the pattern
            documents = await self.retriever.retrieve_by_source(source_pattern)
            
            if not documents:
                logger.info(f"No documents found matching pattern: {source_pattern}")
                return True
            
            # Extract unique document IDs
            doc_ids = list(set(doc.get("metadata", {}).get("doc_id") for doc in documents))
            doc_ids = [doc_id for doc_id in doc_ids if doc_id]
            
            if doc_ids:
                success = await self.processor.milvus_manager.delete_documents(doc_ids)
                if success:
                    logger.info(f"Deleted {len(doc_ids)} documents matching pattern: {source_pattern}")
                return success
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete documents: {str(e)}")
            return False
    
    async def process_data_stream(self, data_stream: AsyncGenerator[Dict[str, Any], None]) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.is_initialized:
            raise RuntimeError("RAG Manager not initialized")
        
        async for result in self.processor.process_data_stream(data_stream):
            yield result
    
    async def export_collection_info(self, output_file: str) -> bool:
        try:
            stats = await self.get_collection_stats()
            
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "collection_stats": stats,
                "config": {
                    "chunk_size": self.config.chunk_size,
                    "chunk_overlap": self.config.chunk_overlap,
                    "embedding_model": self.config.embedding_model,
                    "embedding_dimension": self.config.embedding_dimension,
                    "supported_formats": self.config.supported_formats
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Collection info exported to: {output_file}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export collection info: {str(e)}")
            return False
    
    async def cleanup(self):
        try:
            if self.processor:
                await self.processor.cleanup()
            if self.retriever:
                await self.retriever.cleanup()
            logger.info("RAG Manager cleanup completed")
        except Exception as e:
            logger.error(f"Error during RAG Manager cleanup: {str(e)}")


async def main():
    parser = argparse.ArgumentParser(description="RAG Document Management Tool")
    parser.add_argument("command", choices=["index", "search", "stats", "delete", "export"])
    parser.add_argument("--source", help="Source path for indexing")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results to return")
    parser.add_argument("--doc-types", nargs="+", help="Document types to filter")
    parser.add_argument("--source-filter", help="Source filter pattern")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--config", help="Config file path")
    
    args = parser.parse_args()
    
    # Load configuration
    config = get_config()
    
    # Initialize RAG manager
    rag_manager = RAGManager(config)
    
    try:
        success = await rag_manager.initialize()
        if not success:
            print("Failed to initialize RAG Manager")
            return
        
        if args.command == "index":
            if not args.source:
                print("Source path is required for indexing")
                return
            
            print(f"Indexing documents from: {args.source}")
            result = await rag_manager.index_documents(args.source)
            print(f"Indexing result: {json.dumps(result, indent=2)}")
        
        elif args.command == "search":
            if not args.query:
                print("Query is required for search")
                return
            
            print(f"Searching for: {args.query}")
            results = await rag_manager.search_documents(
                query=args.query,
                top_k=args.top_k,
                document_types=args.doc_types,
                source_filter=args.source_filter
            )
            
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Score: {result.get('score', 0):.3f}")
                print(f"   Source: {result.get('source', 'Unknown')}")
                print(f"   Type: {result.get('doc_type', 'Unknown')}")
                print(f"   Content: {result.get('content', '')[:200]}...")
        
        elif args.command == "stats":
            stats = await rag_manager.get_collection_stats()
            print(f"Collection Statistics:")
            print(json.dumps(stats, indent=2))
        
        elif args.command == "delete":
            if not args.source_filter:
                print("Source filter is required for deletion")
                return
            
            print(f"Deleting documents matching: {args.source_filter}")
            success = await rag_manager.delete_documents_by_source(args.source_filter)
            print(f"Deletion {'successful' if success else 'failed'}")
        
        elif args.command == "export":
            output_file = args.output or f"rag_collection_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            success = await rag_manager.export_collection_info(output_file)
            print(f"Export {'successful' if success else 'failed'}")
    
    finally:
        await rag_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
