#!/usr/bin/env python3
"""
force_cleanup.py - Qdrant collections cleanup

This script deletes ALL collections from the configured Qdrant instance.

Usage:
    python force_cleanup.py [--force] [--dry-run]

Options:
    --force      Skip confirmation prompt
    --dry-run    Show what would be deleted without deleting
"""

import os
import sys
import argparse
import logging
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
        
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if not qdrant_url or not qdrant_api_key:
            logger.warning("QDRANT_URL and QDRANT_API_KEY not set - skipping Qdrant operations")
            return None
        
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        return client
    except ImportError:
        logger.warning("qdrant-client not installed - skipping Qdrant operations")
        return None
    except Exception as e:
        logger.warning(f"Failed to connect to Qdrant: {e}")
        return None

def get_qdrant_collections(client) -> List[Dict[str, Any]]:
    """Get all collections from Qdrant"""
    if not client:
        return []
    
    try:
        collections_response = client.get_collections()
        collections = []
        for c in collections_response.collections:
            # points_count needs extra call per collection in newer clients
            name = c.name if hasattr(c, 'name') else getattr(c, 'collection_name', None)
            points_count = 0
            try:
                if name:
                    info = client.get_collection(name)
                    points_count = getattr(info, 'points_count', 0) or getattr(getattr(info, 'status', {}), 'points_count', 0)
            except Exception:
                points_count = 0
            if name:
                collections.append({'name': name, 'points_count': points_count, 'source': 'qdrant'})
        
        return collections
    except Exception as e:
        logger.error(f"Failed to get Qdrant collections: {e}")
        return []

def force_cleanup(dry_run: bool = False) -> Dict[str, int]:
    """Delete all collections from Qdrant"""
    results = {
        'qdrant_collections_deleted': 0,
        'qdrant_failed': 0
    }
    
    qdrant_client = get_qdrant_client()
    if not qdrant_client:
        logger.error("Qdrant client not available - set QDRANT_URL and QDRANT_API_KEY")
        return results
    
    qdrant_collections = get_qdrant_collections(qdrant_client)
    
    if dry_run:
        logger.info(f"Would delete {len(qdrant_collections)} Qdrant collections")
        for collection in qdrant_collections:
            logger.info(f"  - {collection['name']}: {collection['points_count']} points")
        return results
    
    logger.info(f"Deleting {len(qdrant_collections)} Qdrant collections...")
    for collection in qdrant_collections:
        collection_name = collection['name']
        points_count = collection['points_count']
        try:
            qdrant_client.delete_collection(collection_name)
            logger.info(f"✅ Deleted Qdrant collection: {collection_name} ({points_count} points)")
            results['qdrant_collections_deleted'] += 1
        except Exception as e:
            logger.error(f"❌ Failed to delete Qdrant collection {collection_name}: {e}")
            results['qdrant_failed'] += 1
    
    return results

def confirm_cleanup() -> bool:
    """Ask for user confirmation before cleanup"""
    print(f"\n⚠️  WARNING: You are about to perform a FORCE cleanup!")
    print(f"   This will permanently delete:")
    print(f"   - ALL Qdrant collections in the configured instance")
    
    print(f"\nThis action cannot be undone!")
    
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
    parser = argparse.ArgumentParser(description="Delete ALL collections from Qdrant")
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    
    args = parser.parse_args()
    
    print("🗄️  Qdrant Collections Cleanup")
    print("=" * 50)
    
    # Show dry run results
    if args.dry_run:
        force_cleanup(dry_run=True)
        return
    
    # Confirm cleanup unless forced
    if not args.force:
        if not confirm_cleanup():
            logger.info("Cleanup cancelled by user")
            return
    
    # Perform cleanup
    results = force_cleanup(dry_run=False)
    
    # Show results
    print("\n" + "=" * 50)
    print("📊 CLEANUP RESULTS")
    print("=" * 50)
    print(f"Qdrant collections deleted: {results['qdrant_collections_deleted']}")
    if results['qdrant_failed'] > 0:
        print(f"Qdrant failures: {results['qdrant_failed']}")
    
    if results['qdrant_failed'] > 0:
        print(f"\n⚠️  {results['qdrant_failed']} Qdrant collections failed to delete. Check logs for details.")
        sys.exit(1)
    else:
        print("\n✅ Qdrant cleanup completed successfully!")

if __name__ == "__main__":
    main()
