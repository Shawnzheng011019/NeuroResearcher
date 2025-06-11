import asyncio
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from config import Config

logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        pass


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package is required. Install with: pip install openai")
        
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
        self.dimension = self._get_model_dimension(model)
    
    def _get_model_dimension(self, model: str) -> int:
        dimension_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }
        return dimension_map.get(model, 1536)
    
    async def embed_text(self, text: str) -> List[float]:
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {str(e)}")
            raise
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            # OpenAI has a limit on batch size, so we process in chunks
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
        except Exception as e:
            logger.error(f"OpenAI batch embedding error: {str(e)}")
            raise
    
    def get_dimension(self) -> int:
        return self.dimension


class SentenceTransformerProvider(BaseEmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers package is required. Install with: pip install sentence-transformers")
        
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    async def embed_text(self, text: str) -> List[float]:
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                lambda: self.model.encode([text])[0]
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"SentenceTransformer embedding error: {str(e)}")
            raise
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(texts)
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"SentenceTransformer batch embedding error: {str(e)}")
            raise
    
    def get_dimension(self) -> int:
        return self.dimension


class HuggingFaceEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        if not TORCH_AVAILABLE:
            raise ImportError("torch package is required. Install with: pip install torch")
        
        try:
            from transformers import AutoTokenizer, AutoModel
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)
            self.dimension = self.model.config.hidden_size
        except ImportError:
            raise ImportError("transformers package is required. Install with: pip install transformers")
    
    async def embed_text(self, text: str) -> List[float]:
        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(None, self._encode_text, text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"HuggingFace embedding error: {str(e)}")
            raise
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(None, self._encode_batch, texts)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"HuggingFace batch embedding error: {str(e)}")
            raise
    
    def _encode_text(self, text: str) -> np.ndarray:
        import torch
        
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Use mean pooling
            embeddings = outputs.last_hidden_state.mean(dim=1)
        
        return embeddings.squeeze().numpy()
    
    def _encode_batch(self, texts: List[str]) -> np.ndarray:
        import torch
        
        inputs = self.tokenizer(texts, return_tensors="pt", truncation=True, padding=True)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Use mean pooling
            embeddings = outputs.last_hidden_state.mean(dim=1)
        
        return embeddings.numpy()
    
    def get_dimension(self) -> int:
        return self.dimension


class EmbeddingManager:
    def __init__(self, config: Config):
        self.config = config
        self.provider = self._create_provider()
    
    def _create_provider(self) -> BaseEmbeddingProvider:
        provider_name = self.config.embedding_provider.lower()
        
        if provider_name == "openai":
            if not self.config.openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI embedding provider")
            return OpenAIEmbeddingProvider(
                api_key=self.config.openai_api_key,
                model=self.config.embedding_model
            )
        
        elif provider_name == "sentence_transformers":
            return SentenceTransformerProvider(model_name=self.config.embedding_model)
        
        elif provider_name == "huggingface":
            return HuggingFaceEmbeddingProvider(model_name=self.config.embedding_model)
        
        else:
            raise ValueError(f"Unsupported embedding provider: {provider_name}")
    
    async def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.provider.get_dimension()
        
        return await self.provider.embed_text(text.strip())
    
    async def embed_documents(self, documents: List[Dict[str, Any]]) -> List[List[float]]:
        texts = [doc.get("content", "") for doc in documents]
        
        # Filter out empty texts and keep track of indices
        non_empty_texts = []
        text_indices = []
        
        for i, text in enumerate(texts):
            if text and text.strip():
                non_empty_texts.append(text.strip())
                text_indices.append(i)
        
        if not non_empty_texts:
            # Return zero vectors for all documents
            zero_vector = [0.0] * self.provider.get_dimension()
            return [zero_vector] * len(documents)
        
        # Get embeddings for non-empty texts
        embeddings = await self.provider.embed_batch(non_empty_texts)
        
        # Create result list with zero vectors for empty texts
        result = []
        zero_vector = [0.0] * self.provider.get_dimension()
        embedding_idx = 0
        
        for i in range(len(texts)):
            if i in text_indices:
                result.append(embeddings[embedding_idx])
                embedding_idx += 1
            else:
                result.append(zero_vector)
        
        return result
    
    def get_dimension(self) -> int:
        return self.provider.get_dimension()
    
    async def embed_query(self, query: str) -> List[float]:
        return await self.embed_text(query)


def create_embedding_manager(config: Config) -> EmbeddingManager:
    return EmbeddingManager(config)
