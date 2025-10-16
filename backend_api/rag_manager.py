"""
rag_manager.py - RAG Manager with mandatory Qdrant integration

This module mandates Qdrant as the vector storage. All previous local
storage/BM25 fallback logic has been removed to simplify behavior and
avoid divergent code paths.
"""

import os
import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Mandatory Qdrant client
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Embeddings (Google Generative AI)
import google.generativeai as genai

logger = logging.getLogger(__name__)

class CollectionStatus(Enum):
    """Status of a vector collection"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    DELETED = "deleted"

@dataclass
class CollectionMetadata:
    """Metadata for a vector collection"""
    collection_id: str
    session_id: str
    name: str
    created_at: datetime
    last_accessed: datetime
    document_count: int
    status: CollectionStatus
    description: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class ConsolidatedRAGManager:
    """
    RAG Manager with mandatory Qdrant integration.
    Features:
    - Qdrant vector database integration (required)
    - Session-based collections
    - Automatic cleanup of old collections
    - Collection metadata tracking
    """
    
    def __init__(self, 
                 max_collections: int = 50,
                 collection_ttl_hours: int = 24,
                 auto_cleanup: bool = True,
                 quadrant_url: Optional[str] = None,
                 quadrant_api_key: Optional[str] = None):
        
        self.max_collections = max_collections
        self.collection_ttl_hours = collection_ttl_hours
        self.auto_cleanup = auto_cleanup
        # Initialize Qdrant (mandatory)
        qdrant_url = quadrant_url or os.getenv("QDRANT_URL")
        qdrant_api_key = quadrant_api_key or os.getenv("QDRANT_API_KEY")

        if not qdrant_url or not qdrant_api_key:
            raise RuntimeError(
                "Qdrant is required. Please set QDRANT_URL and QDRANT_API_KEY environment variables."
            )

        try:
            self.qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
            logger.info("Qdrant client initialized successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Qdrant: {e}") from e
        
        # In-memory metadata for collections
        self.collection_metadata: Dict[str, CollectionMetadata] = {}
        
        # Embedding configuration
        self.embedding_model = os.getenv("GOOGLE_EMBEDDING_MODEL", "text-embedding-004")
        self.vector_size = int(os.getenv("QDRANT_VECTOR_SIZE", "768"))
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set; embeddings will fail.")
        else:
            try:
                genai.configure(api_key=api_key)
            except Exception as e:
                logger.warning(f"Failed to configure Generative AI embeddings: {e}")

        logger.info("RAG Manager initialized using Qdrant")
    
    # All on-disk local storage logic has been removed; metadata is kept in-memory only.
    
    def create_collection(self, 
                         session_id: str, 
                         name: Optional[str] = None,
                         description: Optional[str] = None,
                         tags: Optional[List[str]] = None) -> str:
        """Create a new vector collection for a session"""
        # Check if collection already exists for this session
        existing_collection = self.get_collection_by_session(session_id)
        if existing_collection:
            logger.info(f"Collection already exists for session {session_id}: {existing_collection}")
            return existing_collection
        
        # Generate collection ID
        collection_id = str(uuid.uuid4())
        
        # Create collection metadata
        # Make collection name unique and human-readable
        unique_name = (name or f"Session_{session_id[:8]}") + f"_{collection_id[:8]}"
        
        metadata = CollectionMetadata(
            collection_id=collection_id,
            session_id=session_id,
            name=unique_name,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            document_count=0,
            status=CollectionStatus.ACTIVE,
            description=description,
            tags=tags or []
        )
        
        # Create Qdrant collection
        try:
            self.qdrant_client.create_collection(
                collection_name=metadata.name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
            )
            logger.info(f"Created Qdrant collection: {metadata.name}")
        except Exception as e:
            raise RuntimeError(f"Failed to create Qdrant collection: {e}") from e
        
        self.collection_metadata[collection_id] = metadata
        
        # Auto-cleanup if needed
        if self.auto_cleanup:
            self._cleanup_old_collections()
        
        logger.info(f"Created collection {collection_id} for session {session_id}")
        return collection_id
    
    def get_collection_by_session(self, session_id: str) -> Optional[str]:
        """Get collection ID for a session"""
        for collection_id, metadata in self.collection_metadata.items():
            if (metadata.session_id == session_id and 
                metadata.status == CollectionStatus.ACTIVE):
                return collection_id
        return None
    
    def get_or_create_collection(self, session_id: str) -> str:
        """Get existing collection or create new one for session"""
        collection_id = self.get_collection_by_session(session_id)
        if not collection_id:
            collection_id = self.create_collection(session_id)
        else:
            # Update last accessed time
            self.collection_metadata[collection_id].last_accessed = datetime.now()
        
        return collection_id
    
    def add_documents(self, 
                     session_id: str, 
                     documents: List[str],
                     metadata_list: Optional[List[Dict[str, Any]]] = None) -> str:
        """Add documents to a session's collection"""
        collection_id = self.get_or_create_collection(session_id)
        
        # Generate embeddings
        try:
            embeddings = self._embed_texts(documents)
            if not embeddings or len(embeddings) != len(documents):
                raise RuntimeError("Embedding generation failed or returned mismatched sizes")
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return f"Error embedding documents: {e}"

        # Prepare upsert points
        points: List[PointStruct] = []
        for i, (text, vector) in enumerate(zip(documents, embeddings)):
            payload = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
            payload.update({
                "session_id": session_id,
                "text": text,
                "added_at": datetime.now().isoformat(),
            })
            points.append(PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload))

        # Upsert into Qdrant
        try:
            collection_name = self.collection_metadata[collection_id].name
            self.qdrant_client.upsert(collection_name=collection_name, points=points)
        except Exception as e:
            logger.error(f"Qdrant upsert failed: {e}")
            return f"Error storing documents: {e}"

        # Update metadata
        collection_metadata = self.collection_metadata[collection_id]
        collection_metadata.document_count += len(documents)
        collection_metadata.last_accessed = datetime.now()
        logger.info(f"Added {len(documents)} documents to Qdrant collection {collection_name}")
        return f"Added {len(documents)} documents. Total: {collection_metadata.document_count}"
    
    def search_documents(self, 
                        session_id: str, 
                        query: str, 
                        top_k: int = 3) -> List[Dict[str, Any]]:
        """Search documents in a session's collection"""
        collection_id = self.get_collection_by_session(session_id)
        if not collection_id:
            return []
        
        collection_metadata = self.collection_metadata[collection_id]
        
        # Update last accessed time
        collection_metadata.last_accessed = datetime.now()
        
        # Embed query
        try:
            query_vecs = self._embed_texts([query])
            if not query_vecs:
                return []
            query_vector = query_vecs[0]
        except Exception as e:
            logger.error(f"Embedding error on search: {e}")
            return []
        
        # Search Qdrant
        try:
            results = self.qdrant_client.search(
                collection_name=collection_metadata.name,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True
            )
            formatted = []
            for r in results:
                payload = r.payload or {}
                formatted.append({
                    "document": payload.get("text", ""),
                    "metadata": {k: v for k, v in payload.items() if k != "text"},
                    "score": float(r.score) if hasattr(r, 'score') else 0.0
                })
            return formatted
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a list of texts using Google Generative AI (per-text calls)."""
        if not texts:
            return []
        vectors: List[List[float]] = []
        try:
            for t in texts:
                resp = genai.embed_content(model=self.embedding_model, content=t)
                vec = None
                if isinstance(resp, dict):
                    vec = resp.get("embedding") or resp.get("values")
                    # Some SDKs nest under 'embedding': {'values': [...]}
                    if isinstance(vec, dict) and "values" in vec:
                        vec = vec["values"]
                if not isinstance(vec, list):
                    raise RuntimeError("Invalid embedding response format")
                # Normalize dimension
                if len(vec) > self.vector_size:
                    vec = vec[:self.vector_size]
                elif len(vec) < self.vector_size:
                    vec = vec + [0.0] * (self.vector_size - len(vec))
                vectors.append(vec)
            return vectors
        except Exception as e:
            raise RuntimeError(f"Embedding call failed: {e}")
    
    def clear_collection(self, session_id: str) -> str:
        """Clear all documents from a session's collection"""
        collection_id = self.get_collection_by_session(session_id)
        if not collection_id:
            return f"No collection found for session {session_id}"
        
        collection_metadata = self.collection_metadata[collection_id]
        collection_metadata.document_count = 0
        collection_metadata.last_accessed = datetime.now()
        
        try:
            # Use Qdrant collection name (metadata.name)
            self.qdrant_client.delete_collection(self.collection_metadata[collection_id].name)
            logger.info(f"Cleared Qdrant collection {self.collection_metadata[collection_id].name} for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to clear Qdrant collection: {e}")
        
        logger.info(f"Cleared collection {collection_id} for session {session_id}")
        return f"Cleared collection for session {session_id}"
    
    def delete_collection(self, session_id: str) -> str:
        """Delete a session's collection"""
        collection_id = self.get_collection_by_session(session_id)
        if not collection_id:
            return f"No collection found for session {session_id}"
        
        # Mark as deleted
        self.collection_metadata[collection_id].status = CollectionStatus.DELETED
        
        try:
            # Use Qdrant collection name (metadata.name)
            self.qdrant_client.delete_collection(self.collection_metadata[collection_id].name)
            logger.info(f"Deleted Qdrant collection {self.collection_metadata[collection_id].name} for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete Qdrant collection: {e}")
        
        logger.info(f"Deleted collection {collection_id} for session {session_id}")
        return f"Deleted collection for session {session_id}"
    
    def get_collection_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of a session's collection"""
        collection_id = self.get_collection_by_session(session_id)
        if not collection_id:
            return {
                "session_id": session_id,
                "collection_id": None,
                "status": "not_found",
                "document_count": 0,
                "has_documents": False
            }
        
        metadata = self.collection_metadata[collection_id]
        return {
            "session_id": session_id,
            "collection_id": collection_id,
            "status": metadata.status.value,
            "document_count": metadata.document_count,
            "has_documents": metadata.document_count > 0,
            "created_at": metadata.created_at.isoformat(),
            "last_accessed": metadata.last_accessed.isoformat(),
            "name": metadata.name,
            "description": metadata.description,
            "tags": metadata.tags,
            "storage_type": "qdrant"
        }
    
    def list_collections(self, 
                        status: Optional[CollectionStatus] = None,
                        limit: int = 20) -> List[Dict[str, Any]]:
        """List all collections with optional filtering"""
        collections = []
        
        for collection_id, metadata in self.collection_metadata.items():
            if status and metadata.status != status:
                continue
            
            collections.append({
                "collection_id": collection_id,
                "session_id": metadata.session_id,
                "name": metadata.name,
                "status": metadata.status.value,
                "document_count": metadata.document_count,
                "created_at": metadata.created_at.isoformat(),
                "last_accessed": metadata.last_accessed.isoformat(),
                "description": metadata.description,
                "tags": metadata.tags,
                        "storage_type": "qdrant"
            })
        
        # Sort by last accessed time
        collections.sort(key=lambda x: x["last_accessed"], reverse=True)
        
        return collections[:limit]
    
    def _cleanup_old_collections(self):
        """Clean up old collections based on TTL and max collections limit"""
        now = datetime.now()
        ttl_threshold = now - timedelta(hours=self.collection_ttl_hours)
        
        # Find collections to archive
        collections_to_archive = []
        for collection_id, metadata in self.collection_metadata.items():
            if (metadata.status == CollectionStatus.ACTIVE and 
                metadata.last_accessed < ttl_threshold):
                collections_to_archive.append(collection_id)
        
        # Archive old collections
        for collection_id in collections_to_archive:
            self.collection_metadata[collection_id].status = CollectionStatus.ARCHIVED
            logger.info(f"Archived old collection {collection_id}")
        
        # If still over limit, remove oldest archived collections
        if len(self.collection_metadata) > self.max_collections:
            archived_collections = [
                (collection_id, metadata) 
                for collection_id, metadata in self.collection_metadata.items()
                if metadata.status == CollectionStatus.ARCHIVED
            ]
            
            # Sort by last accessed time
            archived_collections.sort(key=lambda x: x[1].last_accessed)
            
            # Remove oldest archived collections
            to_remove = len(self.collection_metadata) - self.max_collections
            for i in range(min(to_remove, len(archived_collections))):
                collection_id = archived_collections[i][0]
                self.collection_metadata[collection_id].status = CollectionStatus.DELETED
                del self.collection_metadata[collection_id]
                logger.info(f"Removed archived collection {collection_id}")
        
        # No on-disk save; metadata is in-memory only
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get manager statistics"""
        active_collections = sum(1 for m in self.collection_metadata.values() 
                               if m.status == CollectionStatus.ACTIVE)
        total_documents = sum(m.document_count for m in self.collection_metadata.values() 
                            if m.status == CollectionStatus.ACTIVE)
        
        return {
            "total_collections": len(self.collection_metadata),
            "active_collections": active_collections,
            "archived_collections": sum(1 for m in self.collection_metadata.values() 
                                      if m.status == CollectionStatus.ARCHIVED),
            "total_documents": total_documents,
            "max_collections": self.max_collections,
            "collection_ttl_hours": self.collection_ttl_hours,
            "auto_cleanup_enabled": self.auto_cleanup,
            "storage_type": "qdrant",
            "quadrant_available": True
        }
    
    def cleanup_old_collections(self):
        """Manually trigger cleanup of old collections"""
        self._cleanup_old_collections()
        return "Cleanup completed"

# Global instance for backward compatibility
_global_rag_manager = None

def get_global_rag_manager() -> ConsolidatedRAGManager:
    """Get the global RAG manager instance"""
    global _global_rag_manager
    if _global_rag_manager is None:
        # Get configuration from environment variables
        quadrant_url = os.getenv("QDRANT_URL")
        quadrant_api_key = os.getenv("QDRANT_API_KEY")
        
        _global_rag_manager = ConsolidatedRAGManager(
            quadrant_url=quadrant_url,
            quadrant_api_key=quadrant_api_key
        )
    return _global_rag_manager

def create_session_rag_manager(session_id: str) -> ConsolidatedRAGManager:
    """Create a new RAG manager instance for a session"""
    quadrant_url = os.getenv("QDRANT_URL")
    quadrant_api_key = os.getenv("QDRANT_API_KEY")
    
    return ConsolidatedRAGManager(
        quadrant_url=quadrant_url,
        quadrant_api_key=quadrant_api_key
    )
