#!/usr/bin/env python3
"""
delete_all_collections.py - Script to delete all collections from Qdrant vector database

This script provides a safe way to clean up all collections from the Qdrant vector database.
It includes confirmation prompts and backup options for safety.

Usage:
    python delete_all_collections.py [--force] [--backup] [--dry-run]
    
Options:
    --force     Skip confirmation prompts
    --backup    Create backup before deletion
    --dry-run   Show what would be deleted without actually deleting
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_qdrant_client():
    """Get Qdrant client using environment variables"""
    try:
        from qdrant_client import QdrantClient
        
        qdrant_url = os.getenv("QUADRANT_URL")
        qdrant_api_key = os.getenv("QUADRANT_API_KEY")
        
        if not qdrant_url or not qdrant_api_key:
            logger.error("QUADRANT_URL and QUADRANT_API_KEY must be set in environment variables")
            return None
        
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        return client
    except ImportError:
        logger.error("qdrant-client not installed. Run: pip install qdrant-client")
        return None
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        return None

def get_all_collections(client) -> List[Dict[str, Any]]:
    """Get all collections from Qdrant"""
    try:
        collections_response = client.get_collections()
        collections = []
        
        for collection in collections_response.collections:
            collection_info = {
                'name': collection.name,
                'status': collection.status,
                'optimizer_status': collection.optimizer_status,
                'vectors_count': collection.vectors_count,
                'indexed_vectors_count': collection.indexed_vectors_count,
                'points_count': collection.points_count,
                'segments_count': collection.segments_count,
                'disk_data_size': collection.disk_data_size,
                'ram_data_size': collection.ram_data_size
            }
            collections.append(collection_info)
        
        return collections
    except Exception as e:
        logger.error(f"Failed to get collections: {e}")
        return []

def backup_collections(collections: List[Dict[str, Any]], backup_file: str = None) -> str:
    """Create a backup of collection information"""
    if not backup_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"collections_backup_{timestamp}.json"
    
    try:
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'total_collections': len(collections),
            'collections': collections
        }
        
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        logger.info(f"Backup created: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return None

def delete_collection(client, collection_name: str) -> bool:
    """Delete a single collection"""
    try:
        client.delete_collection(collection_name)
        logger.info(f"✅ Deleted collection: {collection_name}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to delete collection {collection_name}: {e}")
        return False

def delete_all_collections(client, collections: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, int]:
    """Delete all collections"""
    results = {
        'total': len(collections),
        'deleted': 0,
        'failed': 0
    }
    
    if dry_run:
        logger.info("🔍 DRY RUN - No collections will actually be deleted")
        for collection in collections:
            logger.info(f"Would delete: {collection['name']} ({collection['points_count']} points)")
        return results
    
    logger.info(f"🗑️  Starting deletion of {len(collections)} collections...")
    
    for collection in collections:
        collection_name = collection['name']
        points_count = collection['points_count']
        
        logger.info(f"Deleting {collection_name} ({points_count} points)...")
        
        if delete_collection(client, collection_name):
            results['deleted'] += 1
        else:
            results['failed'] += 1
    
    return results

def confirm_deletion(collections: List[Dict[str, Any]]) -> bool:
    """Ask for user confirmation before deletion"""
    total_points = sum(collection['points_count'] for collection in collections)
    
    print(f"\n⚠️  WARNING: You are about to delete {len(collections)} collections!")
    print(f"   Total points to be deleted: {total_points:,}")
    print(f"   Total disk usage: {sum(collection.get('disk_data_size', 0) for collection in collections):,} bytes")
    
    print("\nCollections to be deleted:")
    for collection in collections:
        print(f"   - {collection['name']}: {collection['points_count']:,} points")
    
    print("\nThis action cannot be undone!")
    
    while True:
        response = input("\nAre you sure you want to continue? (yes/no): ").lower().strip()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Delete all collections from Qdrant vector database")
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--backup', action='store_true', help='Create backup before deletion')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--backup-file', type=str, help='Custom backup file path')
    
    args = parser.parse_args()
    
    print("🗄️  Qdrant Collection Deletion Script")
    print("=" * 50)
    
    # Get Qdrant client
    client = get_qdrant_client()
    if not client:
        sys.exit(1)
    
    # Get all collections
    logger.info("Fetching collections from Qdrant...")
    collections = get_all_collections(client)
    
    if not collections:
        logger.info("No collections found in Qdrant database")
        return
    
    logger.info(f"Found {len(collections)} collections")
    
    # Create backup if requested
    if args.backup:
        backup_file = backup_collections(collections, args.backup_file)
        if not backup_file:
            logger.error("Failed to create backup. Aborting.")
            sys.exit(1)
    
    # Show dry run results
    if args.dry_run:
        delete_all_collections(client, collections, dry_run=True)
        return
    
    # Confirm deletion unless forced
    if not args.force:
        if not confirm_deletion(collections):
            logger.info("Deletion cancelled by user")
            return
    
    # Delete all collections
    results = delete_all_collections(client, collections, dry_run=False)
    
    # Show results
    print("\n" + "=" * 50)
    print("📊 DELETION RESULTS")
    print("=" * 50)
    print(f"Total collections: {results['total']}")
    print(f"Successfully deleted: {results['deleted']}")
    print(f"Failed to delete: {results['failed']}")
    
    if results['failed'] > 0:
        print(f"\n⚠️  {results['failed']} collections failed to delete. Check logs for details.")
        sys.exit(1)
    else:
        print("\n✅ All collections deleted successfully!")
        
        if args.backup:
            print(f"💾 Backup available at: {backup_file}")

if __name__ == "__main__":
    main()
