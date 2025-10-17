from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class QdrantService:
    """Service for interacting with Qdrant Cloud vector database"""
    
    def __init__(self, url: str, api_key: str = None):
        try:
            if api_key:
                # Qdrant Cloud connection
                self.client = QdrantClient(
                    url=url,
                    api_key=api_key
                )
                logger.info(f"Connected to Qdrant Cloud at {url}")
            else:
                # Local connection (fallback)
                self.client = QdrantClient(url=url)
                logger.info(f"Connected to local Qdrant at {url}")
            
            self.collection_name = "ardupilot_docs"
        except Exception as e:
            logger.warning(f"Could not connect to Qdrant: {e}. Vector search will be disabled.")
            self.client = None
    
    def ensure_collection_exists(self, vector_size: int = 768):
        """Ensure the collection exists"""
        if not self.client:
            return False
        
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                )
                logger.info(f"Created collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            return False

    def ensure_collection(self, collection_name: str, vector_size: int = 768) -> bool:
        """Ensure a specific collection exists (used for per-session stores)."""
        if not self.client:
            return False
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            if collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                )
                logger.info(f"Created collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error ensuring collection {collection_name}: {e}")
            return False
    
    def add_documents(self, documents: List[Dict[str, Any]], vectors: List[List[float]]):
        """Add documents with their embeddings to the collection"""
        if not self.client:
            logger.warning("Qdrant client not available")
            return False
        
        try:
            points = []
            for idx, (doc, vector) in enumerate(zip(documents, vectors)):
                points.append(PointStruct(
                    id=idx,
                    vector=vector,
                    payload=doc
                ))
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Added {len(points)} documents to Qdrant")
            return True
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False

    def add_documents_to_collection(self, collection_name: str, documents: List[Dict[str, Any]], vectors: List[List[float]]):
        """Add documents with embeddings to a specific collection."""
        if not self.client:
            logger.warning("Qdrant client not available")
            return False
        try:
            points = []
            for idx, (doc, vector) in enumerate(zip(documents, vectors)):
                points.append(PointStruct(
                    id=idx,
                    vector=vector,
                    payload=doc
                ))
            self.client.upsert(collection_name=collection_name, points=points)
            logger.info(f"Added {len(points)} documents to collection {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error adding documents to {collection_name}: {e}")
            return False
    
    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if not self.client:
            return []
        
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k
            )
            
            return [
                {
                    'score': hit.score,
                    'payload': hit.payload
                }
                for hit in results
            ]
        except Exception as e:
            # Avoid noisy errors if the docs collection does not exist
            message = str(e)
            if "doesn't exist" in message or "Not found: Collection" in message:
                logger.info("Docs collection not found; skipping docs search")
            else:
                logger.error(f"Error searching: {e}")
            return []

    def search_in_collection(self, collection_name: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search in a specific collection."""
        if not self.client:
            return []
        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k
            )
            return [
                {
                    'score': hit.score,
                    'payload': hit.payload
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(f"Error searching in {collection_name}: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if Qdrant is available"""
        return self.client is not None

