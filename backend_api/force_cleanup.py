#!/usr/bin/env python3
"""
force_cleanup.py - Force cleanup of all collections by directly clearing storage

This script directly clears all collections by:
1. Clearing the vector_storage directory
2. Resetting the RAG manager
3. Optionally clearing Qdrant collections

Usage:
    python force_cleanup.py [--qdrant] [--force] [--backup] [--dry-run]
    
Options:
    --qdrant     Also clear Qdrant collections
    --force      Skip confirmation prompts
    --backup     Create backup before deletion
    --dry-run    Show what would be deleted without actually deleting
"""

import os
import sys
import json
import argparse
import logging
import shutil
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
            logger.warning("QUADRANT_URL and QUADRANT_API_KEY not set - skipping Qdrant operations")
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
        
        for collection in collections_response.collections:
            collection_info = {
                'name': collection.name,
                'points_count': collection.points_count,
                'source': 'qdrant'
            }
            collections.append(collection_info)
        
        return collections
    except Exception as e:
        logger.error(f"Failed to get Qdrant collections: {e}")
        return []

def backup_storage(backup_file: str = None) -> str:
    """Create a backup of the storage directory"""
    if not backup_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"storage_backup_{timestamp}"
    
    storage_path = "./vector_storage"
    
    if not os.path.exists(storage_path):
        logger.info("No storage directory to backup")
        return None
    
    try:
        shutil.copytree(storage_path, backup_file)
        logger.info(f"Storage backup created: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Failed to create storage backup: {e}")
        return None

def force_cleanup(qdrant: bool = False, dry_run: bool = False) -> Dict[str, int]:
    """Force cleanup of all collections"""
    results = {
        'storage_cleared': False,
        'qdrant_collections_deleted': 0,
        'qdrant_failed': 0
    }
    
    # Clear local storage
    storage_path = "./vector_storage"
    
    if dry_run:
        logger.info("🔍 DRY RUN - No data will actually be deleted")
        if os.path.exists(storage_path):
            logger.info(f"Would clear storage directory: {storage_path}")
        else:
            logger.info("No storage directory to clear")
    else:
        if os.path.exists(storage_path):
            try:
                shutil.rmtree(storage_path)
                logger.info(f"✅ Cleared storage directory: {storage_path}")
                results['storage_cleared'] = True
            except Exception as e:
                logger.error(f"❌ Failed to clear storage directory: {e}")
        else:
            logger.info("No storage directory to clear")
    
    # Clear Qdrant collections if requested
    if qdrant:
        qdrant_client = get_qdrant_client()
        if qdrant_client:
            qdrant_collections = get_qdrant_collections(qdrant_client)
            
            if dry_run:
                logger.info(f"Would delete {len(qdrant_collections)} Qdrant collections")
                for collection in qdrant_collections:
                    logger.info(f"  - {collection['name']}: {collection['points_count']} points")
            else:
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
        else:
            logger.warning("Qdrant client not available - skipping Qdrant cleanup")
    
    return results

def confirm_cleanup(qdrant: bool = False) -> bool:
    """Ask for user confirmation before cleanup"""
    print(f"\n⚠️  WARNING: You are about to perform a FORCE cleanup!")
    print(f"   This will permanently delete:")
    print(f"   - All local storage files")
    
    if qdrant:
        print(f"   - All Qdrant collections")
    
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
    parser = argparse.ArgumentParser(description="Force cleanup of all collections")
    parser.add_argument('--qdrant', action='store_true', help='Also clear Qdrant collections')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--backup', action='store_true', help='Create backup before deletion')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--backup-file', type=str, help='Custom backup file path')
    
    args = parser.parse_args()
    
    print("🗄️  Force Collection Cleanup Script")
    print("=" * 50)
    
    # Create backup if requested
    backup_file = None
    if args.backup:
        backup_file = backup_storage(args.backup_file)
        if not backup_file and os.path.exists("./vector_storage"):
            logger.error("Failed to create backup. Aborting.")
            sys.exit(1)
    
    # Show dry run results
    if args.dry_run:
        force_cleanup(qdrant=args.qdrant, dry_run=True)
        return
    
    # Confirm cleanup unless forced
    if not args.force:
        if not confirm_cleanup(qdrant=args.qdrant):
            logger.info("Cleanup cancelled by user")
            return
    
    # Perform cleanup
    results = force_cleanup(qdrant=args.qdrant, dry_run=False)
    
    # Show results
    print("\n" + "=" * 50)
    print("📊 CLEANUP RESULTS")
    print("=" * 50)
    print(f"Storage cleared: {'✅' if results['storage_cleared'] else '❌'}")
    
    if args.qdrant:
        print(f"Qdrant collections deleted: {results['qdrant_collections_deleted']}")
        if results['qdrant_failed'] > 0:
            print(f"Qdrant failures: {results['qdrant_failed']}")
    
    if results['qdrant_failed'] > 0:
        print(f"\n⚠️  {results['qdrant_failed']} Qdrant collections failed to delete. Check logs for details.")
        sys.exit(1)
    else:
        print("\n✅ Force cleanup completed successfully!")
        
        if backup_file:
            print(f"💾 Backup available at: {backup_file}")

if __name__ == "__main__":
    main()
