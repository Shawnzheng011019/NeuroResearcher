#!/usr/bin/env python3
"""
RAG Document Management CLI Tool

This tool provides command-line interface for managing documents in the RAG system.
It supports indexing documents, searching, and managing the Milvus collection.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
import logging

from tools.rag_manager import RAGManager
from config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def index_command(args):
    """Index documents from a source path"""
    config = get_config()
    rag_manager = RAGManager(config)
    
    try:
        print("Initializing RAG Manager...")
        success = await rag_manager.initialize()
        if not success:
            print("❌ Failed to initialize RAG Manager")
            return 1
        
        print(f"📁 Indexing documents from: {args.source}")
        result = await rag_manager.index_documents(args.source)
        
        if result["type"] == "directory":
            stats = result["result"]
            print(f"✅ Indexing completed!")
            print(f"   📊 Total files: {stats['total_files']}")
            print(f"   ✅ Processed: {stats['processed_files']}")
            print(f"   ❌ Failed: {stats['failed_files']}")
            print(f"   📄 Total chunks: {stats['total_chunks']}")
            print(f"   ⏱️  Processing time: {stats['processing_time']:.2f}s")
            
            if stats['errors']:
                print(f"   ⚠️  Errors encountered:")
                for error in stats['errors'][:5]:  # Show first 5 errors
                    print(f"      - {error}")
        else:
            file_result = result["result"]
            if file_result["status"] == "success":
                print(f"✅ File indexed successfully!")
                print(f"   📄 Chunks created: {file_result['chunks_created']}")
            else:
                print(f"❌ Failed to index file: {file_result.get('error', 'Unknown error')}")
        
        return 0
    
    except Exception as e:
        print(f"❌ Error during indexing: {str(e)}")
        return 1
    
    finally:
        await rag_manager.cleanup()


async def search_command(args):
    """Search documents using RAG"""
    config = get_config()
    rag_manager = RAGManager(config)
    
    try:
        print("Initializing RAG Manager...")
        success = await rag_manager.initialize()
        if not success:
            print("❌ Failed to initialize RAG Manager")
            return 1
        
        print(f"🔍 Searching for: '{args.query}'")
        results = await rag_manager.search_documents(
            query=args.query,
            top_k=args.top_k,
            document_types=args.doc_types,
            source_filter=args.source_filter,
            similarity_threshold=args.threshold
        )
        
        if not results:
            print("📭 No results found")
            return 0
        
        print(f"📋 Found {len(results)} results:")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            score = result.get('score', 0)
            source = result.get('source', 'Unknown')
            doc_type = result.get('doc_type', 'Unknown')
            content = result.get('content', '')
            
            print(f"\n{i}. 📄 Score: {score:.3f} | Type: {doc_type}")
            print(f"   📂 Source: {source}")
            print(f"   📝 Content: {content[:200]}{'...' if len(content) > 200 else ''}")
        
        return 0
    
    except Exception as e:
        print(f"❌ Error during search: {str(e)}")
        return 1
    
    finally:
        await rag_manager.cleanup()


async def stats_command(args):
    """Show collection statistics"""
    config = get_config()
    rag_manager = RAGManager(config)
    
    try:
        print("Initializing RAG Manager...")
        success = await rag_manager.initialize()
        if not success:
            print("❌ Failed to initialize RAG Manager")
            return 1
        
        print("📊 Retrieving collection statistics...")
        stats = await rag_manager.get_collection_stats()
        
        print("📈 Collection Statistics:")
        print("=" * 50)
        
        milvus_stats = stats.get("milvus_stats", {})
        print(f"📄 Total documents: {milvus_stats.get('total_documents', 0)}")
        print(f"🗂️  Collection name: {milvus_stats.get('collection_name', 'N/A')}")
        print(f"📐 Embedding dimension: {stats.get('embedding_dimension', 'N/A')}")
        print(f"✂️  Chunk size: {stats.get('chunk_size', 'N/A')}")
        print(f"🔗 Chunk overlap: {stats.get('chunk_overlap', 'N/A')}")
        
        return 0
    
    except Exception as e:
        print(f"❌ Error retrieving stats: {str(e)}")
        return 1
    
    finally:
        await rag_manager.cleanup()


async def delete_command(args):
    """Delete documents by source pattern"""
    config = get_config()
    rag_manager = RAGManager(config)
    
    try:
        print("Initializing RAG Manager...")
        success = await rag_manager.initialize()
        if not success:
            print("❌ Failed to initialize RAG Manager")
            return 1
        
        # Confirm deletion
        if not args.force:
            response = input(f"⚠️  Are you sure you want to delete documents matching '{args.pattern}'? (y/N): ")
            if response.lower() != 'y':
                print("❌ Deletion cancelled")
                return 0
        
        print(f"🗑️  Deleting documents matching: {args.pattern}")
        success = await rag_manager.delete_documents_by_source(args.pattern)
        
        if success:
            print("✅ Documents deleted successfully")
        else:
            print("❌ Failed to delete documents")
            return 1
        
        return 0
    
    except Exception as e:
        print(f"❌ Error during deletion: {str(e)}")
        return 1
    
    finally:
        await rag_manager.cleanup()


async def export_command(args):
    """Export collection information"""
    config = get_config()
    rag_manager = RAGManager(config)
    
    try:
        print("Initializing RAG Manager...")
        success = await rag_manager.initialize()
        if not success:
            print("❌ Failed to initialize RAG Manager")
            return 1
        
        output_file = args.output or f"rag_collection_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        print(f"📤 Exporting collection info to: {output_file}")
        success = await rag_manager.export_collection_info(output_file)
        
        if success:
            print(f"✅ Collection info exported to: {output_file}")
        else:
            print("❌ Failed to export collection info")
            return 1
        
        return 0
    
    except Exception as e:
        print(f"❌ Error during export: {str(e)}")
        return 1
    
    finally:
        await rag_manager.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="RAG Document Management CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Index a directory of documents
  python rag_cli.py index --source ./my-docs

  # Index a single file
  python rag_cli.py index --source ./document.pdf

  # Search for documents
  python rag_cli.py search --query "machine learning algorithms"

  # Search with filters
  python rag_cli.py search --query "AI" --doc-types pdf txt --top-k 5

  # Show collection statistics
  python rag_cli.py stats

  # Delete documents by source pattern
  python rag_cli.py delete --pattern "old_docs" --force

  # Export collection information
  python rag_cli.py export --output collection_backup.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Index command
    index_parser = subparsers.add_parser('index', help='Index documents')
    index_parser.add_argument('--source', required=True, help='Source file or directory path')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search documents')
    search_parser.add_argument('--query', required=True, help='Search query')
    search_parser.add_argument('--top-k', type=int, default=10, help='Number of results to return')
    search_parser.add_argument('--doc-types', nargs='+', help='Document types to filter')
    search_parser.add_argument('--source-filter', help='Source filter pattern')
    search_parser.add_argument('--threshold', type=float, help='Similarity threshold')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show collection statistics')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete documents')
    delete_parser.add_argument('--pattern', required=True, help='Source pattern to match for deletion')
    delete_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export collection information')
    export_parser.add_argument('--output', help='Output file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Run the appropriate command
    if args.command == 'index':
        return asyncio.run(index_command(args))
    elif args.command == 'search':
        return asyncio.run(search_command(args))
    elif args.command == 'stats':
        return asyncio.run(stats_command(args))
    elif args.command == 'delete':
        return asyncio.run(delete_command(args))
    elif args.command == 'export':
        return asyncio.run(export_command(args))
    else:
        print(f"❌ Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
