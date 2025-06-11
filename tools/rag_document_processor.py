import asyncio
import logging
import os
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from pathlib import Path
import hashlib
from datetime import datetime

from langchain_community.document_loaders import (
    PyMuPDFLoader,
    TextLoader,
    UnstructuredCSVLoader,
    UnstructuredExcelLoader,
    UnstructuredMarkdownLoader,
    UnstructuredPowerPointLoader,
    UnstructuredWordDocumentLoader,
    JSONLoader,
    UnstructuredXMLLoader,
    BSHTMLLoader
)

from .rag_tools import DocumentChunker, StructuredDataProcessor, DataStreamProcessor
from .embedding_manager import EmbeddingManager
from .milvus_manager import MilvusManager
from config import Config

logger = logging.getLogger(__name__)


class RAGDocumentProcessor:
    def __init__(self, config: Config):
        self.config = config
        self.chunker = DocumentChunker(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )
        self.structured_processor = StructuredDataProcessor()
        self.stream_processor = DataStreamProcessor(
            batch_size=config.stream_batch_size,
            processing_interval=config.stream_processing_interval
        )
        self.embedding_manager = EmbeddingManager(config)
        self.milvus_manager = MilvusManager(config)
        
        self.document_loaders = {
            "pdf": PyMuPDFLoader,
            "txt": TextLoader,
            "doc": UnstructuredWordDocumentLoader,
            "docx": UnstructuredWordDocumentLoader,
            "pptx": UnstructuredPowerPointLoader,
            "md": UnstructuredMarkdownLoader,
            "html": BSHTMLLoader,
            "htm": BSHTMLLoader,
            "csv": UnstructuredCSVLoader,
            "xlsx": UnstructuredExcelLoader,
            "json": JSONLoader,
            "xml": UnstructuredXMLLoader
        }
    
    async def initialize(self) -> bool:
        try:
            # Connect to Milvus
            success = await self.milvus_manager.connect()
            if not success:
                logger.error("Failed to connect to Milvus")
                return False
            
            logger.info("RAG Document Processor initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize RAG Document Processor: {str(e)}")
            return False
    
    async def process_directory(self, directory_path: str) -> Dict[str, Any]:
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Directory does not exist: {directory_path}")
        
        results = {
            "total_files": 0,
            "processed_files": 0,
            "failed_files": 0,
            "total_chunks": 0,
            "processing_time": 0,
            "errors": []
        }
        
        start_time = datetime.now()
        
        # Get all supported files
        supported_files = []
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                file_extension = file_path.suffix.lower().lstrip(".")
                if file_extension in self.config.supported_formats:
                    supported_files.append(file_path)
        
        results["total_files"] = len(supported_files)
        
        # Process files in batches
        batch_size = 10
        for i in range(0, len(supported_files), batch_size):
            batch = supported_files[i:i + batch_size]
            batch_results = await self._process_file_batch(batch)
            
            results["processed_files"] += batch_results["processed"]
            results["failed_files"] += batch_results["failed"]
            results["total_chunks"] += batch_results["chunks"]
            results["errors"].extend(batch_results["errors"])
        
        end_time = datetime.now()
        results["processing_time"] = (end_time - start_time).total_seconds()
        
        logger.info(f"Directory processing completed: {results}")
        return results
    
    async def process_file(self, file_path: str) -> Dict[str, Any]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise ValueError(f"File does not exist: {file_path}")
        
        file_extension = file_path.suffix.lower().lstrip(".")
        
        try:
            if file_extension in ["csv", "xlsx", "json", "xml"]:
                # Process structured data
                chunks = await self._process_structured_file(str(file_path), file_extension)
            else:
                # Process unstructured documents
                chunks = await self._process_unstructured_file(str(file_path), file_extension)
            
            if chunks:
                # Generate embeddings and store in Milvus
                await self._store_chunks_in_milvus(chunks)
                
                return {
                    "status": "success",
                    "file_path": str(file_path),
                    "chunks_created": len(chunks),
                    "file_type": file_extension
                }
            else:
                return {
                    "status": "failed",
                    "file_path": str(file_path),
                    "error": "No chunks created",
                    "file_type": file_extension
                }
        
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {str(e)}")
            return {
                "status": "failed",
                "file_path": str(file_path),
                "error": str(e),
                "file_type": file_extension
            }
    
    async def _process_file_batch(self, file_batch: List[Path]) -> Dict[str, Any]:
        tasks = [self.process_file(str(file_path)) for file_path in file_batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed = 0
        failed = 0
        chunks = 0
        errors = []
        
        for result in results:
            if isinstance(result, Exception):
                failed += 1
                errors.append(str(result))
            elif result["status"] == "success":
                processed += 1
                chunks += result["chunks_created"]
            else:
                failed += 1
                errors.append(result.get("error", "Unknown error"))
        
        return {
            "processed": processed,
            "failed": failed,
            "chunks": chunks,
            "errors": errors
        }
    
    async def _process_unstructured_file(self, file_path: str, file_extension: str) -> List[Dict[str, Any]]:
        try:
            # Load document using appropriate loader
            loader_class = self.document_loaders.get(file_extension)
            if not loader_class:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            loader = loader_class(file_path)
            documents = loader.load()
            
            if not documents:
                return []
            
            # Combine all document content
            combined_content = "\n\n".join([doc.page_content for doc in documents])
            
            # Generate document ID
            doc_id = self._generate_doc_id(file_path)
            
            # Create metadata
            metadata = {
                "source": file_path,
                "type": file_extension,
                "doc_id": doc_id,
                "file_size": os.path.getsize(file_path),
                "created_at": datetime.now().isoformat()
            }
            
            # Chunk the document
            chunks = self.chunker.chunk_document(combined_content, metadata)
            
            return chunks
        
        except Exception as e:
            logger.error(f"Failed to process unstructured file {file_path}: {str(e)}")
            return []
    
    async def _process_structured_file(self, file_path: str, file_extension: str) -> List[Dict[str, Any]]:
        try:
            if file_extension == "csv":
                return await self.structured_processor.process_csv(file_path)
            elif file_extension == "xlsx":
                return await self.structured_processor.process_excel(file_path)
            elif file_extension == "json":
                return await self.structured_processor.process_json(file_path)
            elif file_extension == "xml":
                return await self.structured_processor.process_xml(file_path)
            else:
                raise ValueError(f"Unsupported structured file type: {file_extension}")
        
        except Exception as e:
            logger.error(f"Failed to process structured file {file_path}: {str(e)}")
            return []
    
    async def _store_chunks_in_milvus(self, chunks: List[Dict[str, Any]]) -> bool:
        try:
            # Generate embeddings for all chunks
            embeddings = await self.embedding_manager.embed_documents(chunks)
            
            # Store in Milvus
            success = await self.milvus_manager.insert_documents(chunks, embeddings)
            
            if success:
                logger.info(f"Successfully stored {len(chunks)} chunks in Milvus")
            else:
                logger.error(f"Failed to store {len(chunks)} chunks in Milvus")
            
            return success
        
        except Exception as e:
            logger.error(f"Failed to store chunks in Milvus: {str(e)}")
            return False
    
    async def process_data_stream(self, data_stream: AsyncGenerator[Dict[str, Any], None]) -> AsyncGenerator[Dict[str, Any], None]:
        async for batch in self.stream_processor.process_stream(data_stream):
            try:
                # Store batch in Milvus
                success = await self._store_chunks_in_milvus(batch)
                
                yield {
                    "status": "success" if success else "failed",
                    "batch_size": len(batch),
                    "timestamp": datetime.now().isoformat()
                }
            
            except Exception as e:
                logger.error(f"Failed to process data stream batch: {str(e)}")
                yield {
                    "status": "failed",
                    "batch_size": len(batch),
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
    
    async def search_documents(self, query: str, top_k: int = 10, 
                             filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        try:
            # Generate query embedding
            query_embedding = await self.embedding_manager.embed_query(query)
            
            # Build filter expression if metadata filter is provided
            filter_expr = None
            if filter_metadata:
                filter_conditions = []
                for key, value in filter_metadata.items():
                    if isinstance(value, str):
                        filter_conditions.append(f'{key} == "{value}"')
                    else:
                        filter_conditions.append(f'{key} == {value}')
                filter_expr = " and ".join(filter_conditions)
            
            # Search in Milvus
            results = await self.milvus_manager.search_similar(
                query_embedding=query_embedding,
                top_k=top_k,
                filter_expr=filter_expr
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Failed to search documents: {str(e)}")
            return []
    
    def _generate_doc_id(self, file_path: str) -> str:
        # Generate unique document ID based on file path and modification time
        stat = os.stat(file_path)
        content = f"{file_path}_{stat.st_mtime}_{stat.st_size}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get_stats(self) -> Dict[str, Any]:
        try:
            milvus_stats = await self.milvus_manager.get_collection_stats()
            return {
                "milvus_stats": milvus_stats,
                "embedding_dimension": self.embedding_manager.get_dimension(),
                "chunk_size": self.config.chunk_size,
                "chunk_overlap": self.config.chunk_overlap
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}")
            return {}
    
    async def cleanup(self):
        try:
            await self.milvus_manager.disconnect()
            logger.info("RAG Document Processor cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


def create_rag_processor(config: Config) -> RAGDocumentProcessor:
    return RAGDocumentProcessor(config)
