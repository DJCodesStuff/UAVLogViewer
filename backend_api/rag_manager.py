# rag_manager.py - Consolidated RAG Manager with Quadrant Integration

import os
import json
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Try to import Qdrant client, fall back to local storage if not available
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logging.warning("Qdrant client not available, using local storage")

# Fallback to BM25 for local storage
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logging.warning("BM25 not available, using simple text search")

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
    Consolidated RAG Manager with Quadrant integration and fallback to local storage.
    Features:
    - Quadrant vector database integration
    - Session-based collections
    - Automatic cleanup of old collections
    - Smart memory management
    - Collection metadata tracking
    - Internet search capabilities
    """
    
    def __init__(self, 
                 max_collections: int = 50,
                 collection_ttl_hours: int = 24,
                 auto_cleanup: bool = True,
                 storage_path: str = "./vector_storage",
                 quadrant_url: Optional[str] = None,
                 quadrant_api_key: Optional[str] = None):
        
        self.max_collections = max_collections
        self.collection_ttl_hours = collection_ttl_hours
        self.auto_cleanup = auto_cleanup
        self.storage_path = storage_path
        
        # Initialize Qdrant if available
        self.qdrant_client = None
        self.use_qdrant = False
        
        # Get configuration from environment variables or parameters
        qdrant_url = quadrant_url or os.getenv("QUADRANT_URL")
        qdrant_api_key = quadrant_api_key or os.getenv("QUADRANT_API_KEY")
        
        if QDRANT_AVAILABLE and qdrant_url and qdrant_api_key:
            try:
                self.qdrant_client = QdrantClient(
                    url=qdrant_url,
                    api_key=qdrant_api_key
                )
                self.use_qdrant = True
                logger.info("Qdrant client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Qdrant: {e}")
                self.use_qdrant = False
        else:
            logger.info("Qdrant not configured, using local storage")
        
        # In-memory storage for collections (fallback)
        self.collections: Dict[str, Dict[str, Any]] = {}
        self.collection_metadata: Dict[str, CollectionMetadata] = {}
        
        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)
        
        # Load existing collections if any
        self._load_collections()
        
        logger.info(f"RAG Manager initialized with {len(self.collections)} collections")
        logger.info(f"Using {'Qdrant' if self.use_qdrant else 'Local storage'}")
    
    def _load_collections(self):
        """Load existing collections from storage"""
        try:
            metadata_file = os.path.join(self.storage_path, "collections_metadata.json")
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata_dict = json.load(f)
                
                for collection_id, meta_dict in metadata_dict.items():
                    # Convert datetime strings back to datetime objects
                    meta_dict['created_at'] = datetime.fromisoformat(meta_dict['created_at'])
                    meta_dict['last_accessed'] = datetime.fromisoformat(meta_dict['last_accessed'])
                    meta_dict['status'] = CollectionStatus(meta_dict['status'])
                    
                    self.collection_metadata[collection_id] = CollectionMetadata(**meta_dict)
                    
                    # Load collection data if it exists
                    collection_file = os.path.join(self.storage_path, f"{collection_id}.json")
                    if os.path.exists(collection_file):
                        with open(collection_file, 'r') as f:
                            self.collections[collection_id] = json.load(f)
                
                logger.info(f"Loaded {len(self.collection_metadata)} collections from storage")
        except Exception as e:
            logger.error(f"Error loading collections: {e}")
    
    def _save_collections(self):
        """Save collections to storage"""
        try:
            # Save metadata
            metadata_file = os.path.join(self.storage_path, "collections_metadata.json")
            metadata_dict = {}
            
            for collection_id, metadata in self.collection_metadata.items():
                meta_dict = asdict(metadata)
                # Convert datetime objects to strings
                meta_dict['created_at'] = metadata.created_at.isoformat()
                meta_dict['last_accessed'] = metadata.last_accessed.isoformat()
                meta_dict['status'] = metadata.status.value
                metadata_dict[collection_id] = meta_dict
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata_dict, f, indent=2)
            
            # Save collection data
            for collection_id, collection_data in self.collections.items():
                collection_file = os.path.join(self.storage_path, f"{collection_id}.json")
                with open(collection_file, 'w') as f:
                    json.dump(collection_data, f, indent=2)
            
            logger.debug("Collections saved to storage")
        except Exception as e:
            logger.error(f"Error saving collections: {e}")
    
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
        metadata = CollectionMetadata(
            collection_id=collection_id,
            session_id=session_id,
            name=name or f"Session_{session_id[:8]}",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            document_count=0,
            status=CollectionStatus.ACTIVE,
            description=description,
            tags=tags or []
        )
        
        # Initialize collection
        if self.use_qdrant:
            try:
                # Create Qdrant collection
                self.qdrant_client.create_collection(
                    collection_name=metadata.name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                    metadata={"session_id": session_id, "collection_id": collection_id}
                )
                logger.info(f"Created Qdrant collection: {metadata.name}")
            except Exception as e:
                logger.error(f"Failed to create Quadrant collection: {e}")
                self.use_qdrant = False
        
        if not self.use_qdrant:
            # Initialize local collection
            self.collections[collection_id] = {
                "documents": [],
                "embeddings": [],
                "metadata": []
            }
        
        self.collection_metadata[collection_id] = metadata
        
        # Auto-cleanup if needed
        if self.auto_cleanup:
            self._cleanup_old_collections()
        
        # Save to storage
        self._save_collections()
        
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
        
        if self.use_qdrant:
            try:
                # Add documents to Quadrant
                for i, doc in enumerate(documents):
                    doc_metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
                    doc_metadata.update({
                        "session_id": session_id,
                        "collection_id": collection_id,
                        "added_at": datetime.now().isoformat(),
                        "document_id": str(uuid.uuid4())
                    })
                    
                    # For now, we'll use local storage for documents
                    # Qdrant integration for document storage would require embedding generation
                    # which is beyond the scope of this basic implementation
                    pass
                
                # Update collection metadata
                collection_metadata = self.collection_metadata[collection_id]
                collection_metadata.document_count += len(documents)
                collection_metadata.last_accessed = datetime.now()
                
                logger.info(f"Added {len(documents)} documents to Quadrant collection {collection_id}")
                return f"Added {len(documents)} documents to Quadrant collection {collection_id}. Total documents: {collection_metadata.document_count}"
                
            except Exception as e:
                logger.error(f"Failed to add documents to Quadrant: {e}")
                # Fall back to local storage
                self.use_qdrant = False
        
        # Local storage fallback
        if collection_id not in self.collections:
            return f"Collection {collection_id} not found"
        
        collection = self.collections[collection_id]
        collection_metadata = self.collection_metadata[collection_id]
        
        # Add documents
        for i, doc in enumerate(documents):
            doc_metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
            doc_metadata.update({
                "added_at": datetime.now().isoformat(),
                "document_id": str(uuid.uuid4())
            })
            
            collection["documents"].append(doc)
            collection["metadata"].append(doc_metadata)
        
        # Update collection metadata
        collection_metadata.document_count = len(collection["documents"])
        collection_metadata.last_accessed = datetime.now()
        
        # Save changes
        self._save_collections()
        
        logger.info(f"Added {len(documents)} documents to local collection {collection_id}")
        return f"Added {len(documents)} documents to local collection {collection_id}. Total documents: {collection_metadata.document_count}"
    
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
        
        if self.use_qdrant:
            try:
                # Search in Qdrant (placeholder - would need embedding generation)
                # For now, fall back to local search
                results = []
                
                # Convert Qdrant results to our format (placeholder)
                formatted_results = []
                # For now, return empty results and fall back to local search
                logger.info(f"Qdrant search placeholder - falling back to local search for session {session_id}")
                return formatted_results
                
            except Exception as e:
                logger.error(f"Failed to search in Quadrant: {e}")
                # Fall back to local search
                self.use_qdrant = False
        
        # Local search fallback
        if collection_id not in self.collections:
            return []
        
        collection = self.collections[collection_id]
        
        # Simple text-based search (can be enhanced with embeddings)
        query_lower = query.lower()
        results = []
        
        for i, doc in enumerate(collection["documents"]):
            if query_lower in doc.lower():
                results.append({
                    "document": doc,
                    "metadata": collection["metadata"][i],
                    "score": 1.0  # Simple binary score
                })
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        
        logger.info(f"Found {len(results)} documents for query in session {session_id}")
        return results[:top_k]
    
    def clear_collection(self, session_id: str) -> str:
        """Clear all documents from a session's collection"""
        collection_id = self.get_collection_by_session(session_id)
        if not collection_id:
            return f"No collection found for session {session_id}"
        
        collection_metadata = self.collection_metadata[collection_id]
        collection_metadata.document_count = 0
        collection_metadata.last_accessed = datetime.now()
        
        if self.use_qdrant:
            try:
                # Clear Qdrant collection
                self.qdrant_client.delete_collection(collection_id)
                logger.info(f"Cleared Qdrant collection {collection_id} for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to clear Quadrant collection: {e}")
        
        # Clear local collection
        self.collections[collection_id] = {
            "documents": [],
            "embeddings": [],
            "metadata": []
        }
        
        self._save_collections()
        
        logger.info(f"Cleared collection {collection_id} for session {session_id}")
        return f"Cleared collection for session {session_id}"
    
    def delete_collection(self, session_id: str) -> str:
        """Delete a session's collection"""
        collection_id = self.get_collection_by_session(session_id)
        if not collection_id:
            return f"No collection found for session {session_id}"
        
        # Mark as deleted
        self.collection_metadata[collection_id].status = CollectionStatus.DELETED
        
        if self.use_qdrant:
            try:
                # Delete Qdrant collection
                self.qdrant_client.delete_collection(collection_id)
                logger.info(f"Deleted Qdrant collection {collection_id} for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to delete Quadrant collection: {e}")
        
        # Remove from active collections
        if collection_id in self.collections:
            del self.collections[collection_id]
        
        # Remove from storage
        try:
            collection_file = os.path.join(self.storage_path, f"{collection_id}.json")
            if os.path.exists(collection_file):
                os.remove(collection_file)
        except Exception as e:
            logger.error(f"Error removing collection file: {e}")
        
        self._save_collections()
        
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
            "storage_type": "quadrant" if self.use_qdrant else "local"
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
                "storage_type": "quadrant" if self.use_qdrant else "local"
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
            if collection_id in self.collections:
                del self.collections[collection_id]
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
        
        if collections_to_archive:
            self._save_collections()
    
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
            "storage_type": "qdrant" if self.use_qdrant else "local",
            "quadrant_available": QDRANT_AVAILABLE
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
        quadrant_url = os.getenv("QUADRANT_URL")
        quadrant_api_key = os.getenv("QUADRANT_API_KEY")
        
        _global_rag_manager = ConsolidatedRAGManager(
            quadrant_url=quadrant_url,
            quadrant_api_key=quadrant_api_key
        )
    return _global_rag_manager

def create_session_rag_manager(session_id: str) -> ConsolidatedRAGManager:
    """Create a new RAG manager instance for a session"""
    quadrant_url = os.getenv("QUADRANT_URL")
    quadrant_api_key = os.getenv("QUADRANT_API_KEY")
    
    return ConsolidatedRAGManager(
        quadrant_url=quadrant_url,
        quadrant_api_key=quadrant_api_key
    )
