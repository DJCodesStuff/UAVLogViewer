#!/usr/bin/env python3
"""
simple_cleanup.py - Simple script to delete all collections using RAG manager methods

This script uses the RAG manager's built-in methods to clean up all collections.
It's simpler and more reliable than trying to manage collections directly.

Usage:
    python simple_cleanup.py [--force] [--backup] [--dry-run]
    
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

def get_all_collections() -> List[Dict[str, Any]]:
    """Get all collections from RAG manager"""
    try:
        from rag_manager import get_global_rag_manager
        
        rag_manager = get_global_rag_manager()
        collections = rag_manager.list_collections()
        
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

def delete_all_collections(dry_run: bool = False) -> Dict[str, int]:
    """Delete all collections using RAG manager methods"""
    results = {
        'total': 0,
        'deleted': 0,
        'failed': 0
    }
    
    try:
        from rag_manager import get_global_rag_manager
        
        rag_manager = get_global_rag_manager()
        collections = rag_manager.list_collections()
        results['total'] = len(collections)
        
        if dry_run:
            logger.info("🔍 DRY RUN - No collections will actually be deleted")
            for collection in collections:
                logger.info(f"Would delete: {collection['collection_id']} ({collection['document_count']} documents)")
            return results
        
        logger.info(f"🗑️  Starting deletion of {len(collections)} collections...")
        
        for collection in collections:
            collection_id = collection['collection_id']
            document_count = collection['document_count']
            
            logger.info(f"Deleting {collection_id} ({document_count} documents)...")
            
            try:
                # Try to delete the collection
                result = rag_manager.delete_collection(collection_id)
                
                if "successfully" in result.lower() or "deleted" in result.lower():
                    logger.info(f"✅ Deleted collection: {collection_id}")
                    results['deleted'] += 1
                else:
                    logger.error(f"❌ Failed to delete collection {collection_id}: {result}")
                    results['failed'] += 1
                    
            except Exception as e:
                logger.error(f"❌ Failed to delete collection {collection_id}: {e}")
                results['failed'] += 1
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to delete collections: {e}")
        return results

def confirm_deletion(collections: List[Dict[str, Any]]) -> bool:
    """Ask for user confirmation before deletion"""
    total_docs = sum(collection['document_count'] for collection in collections)
    
    print(f"\n⚠️  WARNING: You are about to delete {len(collections)} collections!")
    print(f"   Total documents to be deleted: {total_docs:,}")
    
    print("\nCollections to be deleted:")
    for collection in collections:
        print(f"   - {collection['collection_id']}: {collection['document_count']:,} documents")
    
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
    parser = argparse.ArgumentParser(description="Delete all collections using RAG manager")
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--backup', action='store_true', help='Create backup before deletion')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--backup-file', type=str, help='Custom backup file path')
    
    args = parser.parse_args()
    
    print("🗄️  Simple Collection Cleanup Script")
    print("=" * 50)
    
    # Get all collections
    logger.info("Fetching collections from RAG manager...")
    collections = get_all_collections()
    
    if not collections:
        logger.info("No collections found to delete")
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
        delete_all_collections(dry_run=True)
        return
    
    # Confirm deletion unless forced
    if not args.force:
        if not confirm_deletion(collections):
            logger.info("Deletion cancelled by user")
            return
    
    # Delete all collections
    results = delete_all_collections(dry_run=False)
    
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
