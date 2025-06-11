import asyncio
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

try:
    from pymilvus import (
        connections, Collection, CollectionSchema, FieldSchema, DataType,
        utility, MilvusException
    )
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    logging.warning("PyMilvus not installed. Milvus functionality will be disabled.")

from config import Config

logger = logging.getLogger(__name__)


class MilvusManager:
    def __init__(self, config: Config):
        if not MILVUS_AVAILABLE:
            raise ImportError("PyMilvus is required for Milvus functionality. Install with: pip install pymilvus")
        
        self.config = config
        self.collection_name = config.milvus_collection_name
        self.host = config.milvus_host
        self.port = config.milvus_port
        self.user = config.milvus_user
        self.password = config.milvus_password
        self.dimension = config.embedding_dimension
        
        self.collection = None
        self.is_connected = False
    
    async def connect(self) -> bool:
        try:
            # Connect to Milvus
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password
            )
            
            self.is_connected = True
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
            
            # Initialize collection
            await self._initialize_collection()
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {str(e)}")
            self.is_connected = False
            return False
    
    async def _initialize_collection(self):
        try:
            # Check if collection exists
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"Using existing collection: {self.collection_name}")
            else:
                # Create new collection
                await self._create_collection()
                logger.info(f"Created new collection: {self.collection_name}")
            
            # Load collection
            self.collection.load()
            
        except Exception as e:
            logger.error(f"Failed to initialize collection: {str(e)}")
            raise
    
    async def _create_collection(self):
        # Define schema
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="doc_type", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=32),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="total_chunks", dtype=DataType.INT64)
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description="Research documents collection for RAG"
        )
        
        # Create collection
        self.collection = Collection(
            name=self.collection_name,
            schema=schema
        )
        
        # Create index for vector field
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params
        )
    
    async def insert_documents(self, documents: List[Dict[str, Any]], 
                             embeddings: List[List[float]]) -> bool:
        if not self.is_connected or not self.collection:
            logger.error("Not connected to Milvus or collection not initialized")
            return False
        
        try:
            # Prepare data for insertion
            data = []
            for doc, embedding in zip(documents, embeddings):
                metadata = doc.get("metadata", {})
                
                data.append({
                    "id": metadata.get("chunk_id", f"doc_{len(data)}"),
                    "doc_id": metadata.get("doc_id", "unknown"),
                    "chunk_id": metadata.get("chunk_id", f"chunk_{len(data)}"),
                    "content": doc.get("content", ""),
                    "embedding": embedding,
                    "metadata": json.dumps(metadata),
                    "source": metadata.get("source", "unknown"),
                    "doc_type": metadata.get("type", "unknown"),
                    "created_at": metadata.get("created_at", datetime.now().isoformat()),
                    "chunk_index": metadata.get("chunk_index", 0),
                    "total_chunks": metadata.get("total_chunks", 1)
                })
            
            # Insert data
            insert_result = self.collection.insert(data)
            self.collection.flush()
            
            logger.info(f"Inserted {len(data)} documents into Milvus")
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert documents into Milvus: {str(e)}")
            return False
    
    async def search_similar(self, query_embedding: List[float], 
                           top_k: int = 10, 
                           filter_expr: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_connected or not self.collection:
            logger.error("Not connected to Milvus or collection not initialized")
            return []
        
        try:
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=["doc_id", "chunk_id", "content", "metadata", "source", "doc_type"]
            )
            
            documents = []
            for hits in results:
                for hit in hits:
                    doc = {
                        "id": hit.id,
                        "score": hit.score,
                        "content": hit.entity.get("content"),
                        "metadata": json.loads(hit.entity.get("metadata", "{}")),
                        "source": hit.entity.get("source"),
                        "doc_type": hit.entity.get("doc_type"),
                        "doc_id": hit.entity.get("doc_id"),
                        "chunk_id": hit.entity.get("chunk_id")
                    }
                    documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to search in Milvus: {str(e)}")
            return []
    
    async def delete_documents(self, doc_ids: List[str]) -> bool:
        if not self.is_connected or not self.collection:
            logger.error("Not connected to Milvus or collection not initialized")
            return False
        
        try:
            # Create filter expression
            filter_expr = f"doc_id in {doc_ids}"
            
            # Delete documents
            self.collection.delete(filter_expr)
            self.collection.flush()
            
            logger.info(f"Deleted documents with IDs: {doc_ids}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from Milvus: {str(e)}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        if not self.is_connected or not self.collection:
            return {}
        
        try:
            stats = self.collection.get_stats()
            return {
                "total_documents": stats.get("row_count", 0),
                "collection_name": self.collection_name,
                "dimension": self.dimension
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {}
    
    async def disconnect(self):
        try:
            if self.collection:
                self.collection.release()
            connections.disconnect("default")
            self.is_connected = False
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Error disconnecting from Milvus: {str(e)}")
    
    def __del__(self):
        if self.is_connected:
            try:
                asyncio.create_task(self.disconnect())
            except:
                pass


class MilvusRetriever:
    def __init__(self, milvus_manager: MilvusManager, embedding_function):
        self.milvus_manager = milvus_manager
        self.embedding_function = embedding_function
    
    async def retrieve(self, query: str, top_k: int = 10, 
                      filter_expr: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            # Generate query embedding
            query_embedding = await self.embedding_function(query)
            
            # Search similar documents
            results = await self.milvus_manager.search_similar(
                query_embedding=query_embedding,
                top_k=top_k,
                filter_expr=filter_expr
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve documents: {str(e)}")
            return []
    
    async def retrieve_by_metadata(self, metadata_filter: Dict[str, Any], 
                                 top_k: int = 10) -> List[Dict[str, Any]]:
        try:
            # Build filter expression from metadata
            filter_conditions = []
            for key, value in metadata_filter.items():
                if isinstance(value, str):
                    filter_conditions.append(f'{key} == "{value}"')
                else:
                    filter_conditions.append(f'{key} == {value}')
            
            filter_expr = " and ".join(filter_conditions) if filter_conditions else None
            
            # Use a dummy query embedding (we're filtering by metadata)
            dummy_embedding = [0.0] * self.milvus_manager.dimension
            
            results = await self.milvus_manager.search_similar(
                query_embedding=dummy_embedding,
                top_k=top_k,
                filter_expr=filter_expr
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve documents by metadata: {str(e)}")
            return []
