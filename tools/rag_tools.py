import asyncio
import logging
import json
import pandas as pd
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from pathlib import Path
from datetime import datetime
import hashlib
import io

from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter
)
from .long_text_processor import create_long_text_processor, LongTextProcessor
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    TextLoader,
    UnstructuredCSVLoader,
    UnstructuredExcelLoader,
    UnstructuredMarkdownLoader,
    UnstructuredPowerPointLoader,
    UnstructuredWordDocumentLoader,
    JSONLoader,
    UnstructuredXMLLoader
)
from langchain.schema import Document

logger = logging.getLogger(__name__)


class DocumentChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, config=None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        self.token_splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        # Initialize long text processor if config is available
        self.long_text_processor = None
        if config:
            try:
                self.long_text_processor = create_long_text_processor(config)
            except Exception as e:
                logger.warning(f"Failed to initialize long text processor: {str(e)}")
    
    def chunk_document(self, content: str, metadata: Dict[str, Any], 
                      strategy: str = "recursive") -> List[Dict[str, Any]]:
        if strategy == "recursive":
            splitter = self.text_splitter
        elif strategy == "token":
            splitter = self.token_splitter
        else:
            splitter = CharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
        
        documents = [Document(page_content=content, metadata=metadata)]
        chunks = splitter.split_documents(documents)
        
        result = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = chunk.metadata.copy()
            chunk_metadata.update({
                "chunk_id": f"{metadata.get('doc_id', 'unknown')}_{i}",
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk.page_content),
                "created_at": datetime.now().isoformat()
            })
            
            result.append({
                "content": chunk.page_content,
                "metadata": chunk_metadata
            })
        
        return result

    async def chunk_long_document(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhanced chunking for long documents with summarization"""
        if not self.long_text_processor or not self.config:
            # Fallback to regular chunking
            return self.chunk_document(content, metadata)

        # Check if document is long enough for enhanced processing
        if len(content) < self.config.long_text_threshold:
            return self.chunk_document(content, metadata)

        try:
            logger.info(f"Processing long document with {len(content)} characters")

            # Use long text processor for intelligent chunking and summarization
            processing_result = await self.long_text_processor.process_long_text(
                content, metadata
            )

            # Convert processing result to standard chunk format
            enhanced_chunks = []

            # Add original chunks with summaries
            for i, (chunk, summary_data) in enumerate(zip(
                processing_result.chunks,
                processing_result.chunk_summaries
            )):
                enhanced_metadata = chunk["metadata"].copy()
                enhanced_metadata.update({
                    "has_summary": True,
                    "summary": summary_data.get("summary", ""),
                    "summary_strategy": summary_data.get("strategy", ""),
                    "processing_metadata": processing_result.processing_metadata
                })

                enhanced_chunks.append({
                    "content": chunk["content"],
                    "metadata": enhanced_metadata
                })

            # Add hierarchical summary as a special chunk
            if processing_result.hierarchical_summary:
                summary_chunk = {
                    "content": processing_result.final_summary,
                    "metadata": {
                        **metadata,
                        "chunk_id": f"{metadata.get('doc_id', 'unknown')}_summary",
                        "chunk_type": "document_summary",
                        "is_summary": True,
                        "original_chunks_count": len(processing_result.chunks),
                        "hierarchical_metadata": processing_result.hierarchical_summary.get("metadata", {}),
                        "created_at": datetime.now().isoformat()
                    }
                }
                enhanced_chunks.append(summary_chunk)

            logger.info(f"Enhanced chunking created {len(enhanced_chunks)} chunks (including summary)")
            return enhanced_chunks

        except Exception as e:
            logger.error(f"Long document processing failed, falling back to regular chunking: {str(e)}")
            return self.chunk_document(content, metadata)


class StructuredDataProcessor:
    def __init__(self):
        self.supported_formats = ["csv", "xlsx", "json", "xml"]
    
    async def process_csv(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            df = pd.read_csv(file_path)
            return self._dataframe_to_chunks(df, file_path)
        except Exception as e:
            logger.error(f"Failed to process CSV file {file_path}: {str(e)}")
            return []
    
    async def process_excel(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            chunks = []
            excel_file = pd.ExcelFile(file_path)
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheet_chunks = self._dataframe_to_chunks(df, file_path, str(sheet_name))
                chunks.extend(sheet_chunks)
            
            return chunks
        except Exception as e:
            logger.error(f"Failed to process Excel file {file_path}: {str(e)}")
            return []
    
    async def process_json(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                return self._json_list_to_chunks(data, file_path)
            elif isinstance(data, dict):
                return self._json_dict_to_chunks(data, file_path)
            else:
                content = json.dumps(data, indent=2, ensure_ascii=False)
                return [{
                    "content": content,
                    "metadata": {
                        "source": file_path,
                        "type": "json",
                        "doc_id": self._generate_doc_id(file_path)
                    }
                }]
        except Exception as e:
            logger.error(f"Failed to process JSON file {file_path}: {str(e)}")
            return []
    
    async def process_xml(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            chunks = []
            for element in root.iter():
                if element.text and element.text.strip():
                    content = f"Tag: {element.tag}\nContent: {element.text.strip()}"
                    if element.attrib:
                        content += f"\nAttributes: {json.dumps(element.attrib)}"
                    
                    chunks.append({
                        "content": content,
                        "metadata": {
                            "source": file_path,
                            "type": "xml",
                            "tag": element.tag,
                            "attributes": element.attrib,
                            "doc_id": self._generate_doc_id(file_path)
                        }
                    })
            
            return chunks
        except Exception as e:
            logger.error(f"Failed to process XML file {file_path}: {str(e)}")
            return []
    
    def _dataframe_to_chunks(self, df: pd.DataFrame, file_path: str, 
                           sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
        chunks = []
        
        # Create header chunk
        header_content = f"Columns: {', '.join(df.columns.tolist())}\n"
        header_content += f"Shape: {df.shape[0]} rows, {df.shape[1]} columns\n"
        header_content += f"Data types:\n{df.dtypes.to_string()}"
        
        chunks.append({
            "content": header_content,
            "metadata": {
                "source": file_path,
                "type": "structured_data_header",
                "sheet_name": sheet_name,
                "doc_id": self._generate_doc_id(file_path, sheet_name)
            }
        })
        
        # Create row chunks (batch rows together)
        batch_size = 50
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            content = batch_df.to_string(index=False)
            
            chunks.append({
                "content": content,
                "metadata": {
                    "source": file_path,
                    "type": "structured_data_batch",
                    "sheet_name": sheet_name,
                    "row_start": i,
                    "row_end": min(i + batch_size - 1, len(df) - 1),
                    "doc_id": self._generate_doc_id(file_path, sheet_name, f"batch_{i}")
                }
            })
        
        return chunks
    
    def _json_list_to_chunks(self, data: List[Any], file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        batch_size = 10
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            content = json.dumps(batch, indent=2, ensure_ascii=False)
            
            chunks.append({
                "content": content,
                "metadata": {
                    "source": file_path,
                    "type": "json_batch",
                    "item_start": i,
                    "item_end": min(i + batch_size - 1, len(data) - 1),
                    "doc_id": self._generate_doc_id(file_path, f"batch_{i}")
                }
            })
        
        return chunks
    
    def _json_dict_to_chunks(self, data: Dict[str, Any], file_path: str) -> List[Dict[str, Any]]:
        chunks = []
        
        for key, value in data.items():
            content = f"Key: {key}\nValue: {json.dumps(value, indent=2, ensure_ascii=False)}"
            
            chunks.append({
                "content": content,
                "metadata": {
                    "source": file_path,
                    "type": "json_key_value",
                    "key": key,
                    "doc_id": self._generate_doc_id(file_path, key)
                }
            })
        
        return chunks
    
    def _generate_doc_id(self, file_path: str, *args) -> str:
        content = file_path + "".join(str(arg) for arg in args)
        return hashlib.md5(content.encode()).hexdigest()


class DataStreamProcessor:
    def __init__(self, batch_size: int = 100, processing_interval: int = 60):
        self.batch_size = batch_size
        self.processing_interval = processing_interval
        self.buffer = []
        self.is_processing = False
    
    async def process_stream(self, data_stream: AsyncGenerator[Dict[str, Any], None]) -> AsyncGenerator[List[Dict[str, Any]], None]:
        async for data_item in data_stream:
            self.buffer.append(data_item)
            
            if len(self.buffer) >= self.batch_size:
                batch = self.buffer[:self.batch_size]
                self.buffer = self.buffer[self.batch_size:]
                
                processed_batch = await self._process_batch(batch)
                yield processed_batch
    
    async def _process_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        processed_items = []
        
        for item in batch:
            content = json.dumps(item, indent=2, ensure_ascii=False)
            
            processed_items.append({
                "content": content,
                "metadata": {
                    "source": "data_stream",
                    "type": "stream_data",
                    "timestamp": datetime.now().isoformat(),
                    "doc_id": self._generate_stream_id(item)
                }
            })
        
        return processed_items
    
    def _generate_stream_id(self, item: Dict[str, Any]) -> str:
        content = json.dumps(item, sort_keys=True) + str(datetime.now().timestamp())
        return hashlib.md5(content.encode()).hexdigest()
