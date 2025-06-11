import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .rag_document_processor import RAGDocumentProcessor
from .milvus_manager import MilvusRetriever
from .embedding_manager import EmbeddingManager
from config import Config

logger = logging.getLogger(__name__)


class RAGRetriever:
    def __init__(self, config: Config):
        self.config = config
        self.rag_processor = RAGDocumentProcessor(config)
        self.embedding_manager = EmbeddingManager(config)
        self.milvus_retriever = None
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        try:
            # Initialize RAG processor
            success = await self.rag_processor.initialize()
            if not success:
                return False
            
            # Create Milvus retriever
            self.milvus_retriever = MilvusRetriever(
                milvus_manager=self.rag_processor.milvus_manager,
                embedding_function=self.embedding_manager.embed_query
            )
            
            self.is_initialized = True
            logger.info("RAG Retriever initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize RAG Retriever: {str(e)}")
            return False
    
    async def retrieve_relevant_documents(self, query: str, 
                                        top_k: int = None,
                                        similarity_threshold: float = None,
                                        document_types: Optional[List[str]] = None,
                                        source_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_initialized:
            logger.warning("RAG Retriever not initialized")
            return []
        
        try:
            # Use config defaults if not specified
            top_k = top_k or self.config.top_k_retrieval
            similarity_threshold = similarity_threshold or self.config.similarity_threshold
            
            # Build metadata filter
            filter_metadata = {}
            if document_types:
                # Note: Milvus filter syntax might need adjustment based on version
                filter_metadata["doc_type"] = document_types[0]  # Simplified for now
            
            # Retrieve documents
            results = await self.milvus_retriever.retrieve(
                query=query,
                top_k=top_k,
                filter_expr=self._build_filter_expression(document_types, source_filter)
            )
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in results 
                if result.get("score", 0) >= similarity_threshold
            ]
            
            # Format results for research pipeline
            formatted_results = []
            for result in filtered_results:
                formatted_result = {
                    "content": result.get("content", ""),
                    "source": result.get("source", ""),
                    "score": result.get("score", 0),
                    "metadata": result.get("metadata", {}),
                    "doc_type": result.get("doc_type", "unknown"),
                    "chunk_id": result.get("chunk_id", ""),
                    "url": result.get("source", "")  # For compatibility with existing pipeline
                }
                formatted_results.append(formatted_result)
            
            logger.info(f"Retrieved {len(formatted_results)} relevant documents for query: {query[:100]}...")
            return formatted_results
        
        except Exception as e:
            logger.error(f"Failed to retrieve relevant documents: {str(e)}")
            return []
    
    async def retrieve_by_document_type(self, doc_type: str, 
                                      limit: int = 50) -> List[Dict[str, Any]]:
        if not self.is_initialized:
            logger.warning("RAG Retriever not initialized")
            return []
        
        try:
            results = await self.milvus_retriever.retrieve_by_metadata(
                metadata_filter={"doc_type": doc_type},
                top_k=limit
            )
            
            return self._format_results(results)
        
        except Exception as e:
            logger.error(f"Failed to retrieve documents by type {doc_type}: {str(e)}")
            return []
    
    async def retrieve_by_source(self, source_pattern: str, 
                               limit: int = 50) -> List[Dict[str, Any]]:
        if not self.is_initialized:
            logger.warning("RAG Retriever not initialized")
            return []
        
        try:
            # For now, we'll use a simple approach
            # In production, you might want to use more sophisticated pattern matching
            results = await self.milvus_retriever.retrieve_by_metadata(
                metadata_filter={"source": source_pattern},
                top_k=limit
            )
            
            return self._format_results(results)
        
        except Exception as e:
            logger.error(f"Failed to retrieve documents by source {source_pattern}: {str(e)}")
            return []
    
    async def hybrid_retrieve(self, query: str, 
                            web_results: List[Dict[str, Any]] = None,
                            local_weight: float = 0.7,
                            web_weight: float = 0.3,
                            max_total_results: int = 20) -> List[Dict[str, Any]]:
        """
        Combine local RAG retrieval with web search results
        """
        if not self.is_initialized:
            logger.warning("RAG Retriever not initialized, returning web results only")
            return web_results or []
        
        try:
            # Get local results
            local_k = int(max_total_results * local_weight)
            web_k = int(max_total_results * web_weight)
            
            local_results = await self.retrieve_relevant_documents(
                query=query,
                top_k=local_k
            )
            
            # Combine with web results
            combined_results = []
            
            # Add local results with adjusted scores
            for result in local_results:
                result["score"] = result.get("score", 0) * local_weight
                result["source_type"] = "local"
                combined_results.append(result)
            
            # Add web results with adjusted scores
            if web_results:
                for i, result in enumerate(web_results[:web_k]):
                    # Assign score based on ranking if not present
                    web_score = result.get("score", 1.0 - (i * 0.1)) * web_weight
                    result["score"] = web_score
                    result["source_type"] = "web"
                    combined_results.append(result)
            
            # Sort by combined score
            combined_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            logger.info(f"Hybrid retrieval: {len(local_results)} local + {len(web_results or [])} web results")
            return combined_results[:max_total_results]
        
        except Exception as e:
            logger.error(f"Failed to perform hybrid retrieval: {str(e)}")
            return web_results or []
    
    async def get_document_summary(self, doc_id: str) -> Optional[Dict[str, Any]]:
        if not self.is_initialized:
            return None
        
        try:
            results = await self.milvus_retriever.retrieve_by_metadata(
                metadata_filter={"doc_id": doc_id},
                top_k=100  # Get all chunks for this document
            )
            
            if not results:
                return None
            
            # Aggregate information about the document
            total_chunks = len(results)
            total_content_length = sum(len(r.get("content", "")) for r in results)
            
            # Get metadata from first chunk
            first_chunk = results[0]
            metadata = first_chunk.get("metadata", {})
            
            return {
                "doc_id": doc_id,
                "source": first_chunk.get("source", ""),
                "doc_type": first_chunk.get("doc_type", ""),
                "total_chunks": total_chunks,
                "total_content_length": total_content_length,
                "created_at": metadata.get("created_at", ""),
                "file_size": metadata.get("file_size", 0)
            }
        
        except Exception as e:
            logger.error(f"Failed to get document summary for {doc_id}: {str(e)}")
            return None
    
    def _build_filter_expression(self, document_types: Optional[List[str]] = None,
                               source_filter: Optional[str] = None) -> Optional[str]:
        conditions = []
        
        if document_types:
            # For multiple types, we'd need to use 'in' operator
            # This is a simplified version
            type_conditions = [f'doc_type == "{doc_type}"' for doc_type in document_types]
            if len(type_conditions) == 1:
                conditions.append(type_conditions[0])
            else:
                conditions.append(f"({' or '.join(type_conditions)})")
        
        if source_filter:
            conditions.append(f'source like "%{source_filter}%"')
        
        return " and ".join(conditions) if conditions else None
    
    def _format_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatted_results = []
        for result in results:
            formatted_result = {
                "content": result.get("content", ""),
                "source": result.get("source", ""),
                "score": result.get("score", 0),
                "metadata": result.get("metadata", {}),
                "doc_type": result.get("doc_type", "unknown"),
                "chunk_id": result.get("chunk_id", ""),
                "url": result.get("source", "")
            }
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    async def get_stats(self) -> Dict[str, Any]:
        if not self.is_initialized:
            return {}
        
        return await self.rag_processor.get_stats()
    
    async def cleanup(self):
        if self.rag_processor:
            await self.rag_processor.cleanup()


def create_rag_retriever(config: Config) -> RAGRetriever:
    return RAGRetriever(config)
