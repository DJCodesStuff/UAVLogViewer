import argparse
import sys
import logging

from qdrant_client import QdrantClient

try:
    from config import Config
except Exception as e:
    print(f"Failed to import Config from config.py: {e}")
    sys.exit(1)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("clear_qdrant")


def get_client() -> QdrantClient:
    if not Config.QDRANT_URL:
        raise ValueError("QDRANT_URL is not set in config")
    if Config.QDRANT_API_KEY:
        return QdrantClient(url=Config.QDRANT_URL, api_key=Config.QDRANT_API_KEY)
    return QdrantClient(url=Config.QDRANT_URL)


def list_collections(client: QdrantClient) -> list[str]:
    cols = client.get_collections().collections
    return [c.name for c in cols]


def delete_all_collections(client: QdrantClient, dry_run: bool = False) -> None:
    names = list_collections(client)
    if not names:
        logger.info("No collections found. Nothing to delete.")
        return
    logger.info("Collections detected: %s", ", ".join(names))
    if dry_run:
        logger.info("Dry run enabled. No deletions performed.")
        return
    for name in names:
        logger.info("Deleting collection: %s", name)
        client.delete_collection(collection_name=name)
    logger.info("All collections deleted.")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Delete all Qdrant collections from the configured instance.")
    parser.add_argument("--yes", action="store_true", help="Confirm deletion without interactive prompt")
    parser.add_argument("--dry-run", action="store_true", help="List collections without deleting")
    args = parser.parse_args(argv)

    try:
        client = get_client()
    except Exception as e:
        logger.error("Failed to connect to Qdrant: %s", e)
        return 1

    if not args.yes and not args.dry_run:
        names = list_collections(client)
        if not names:
            logger.info("No collections found. Exiting.")
            return 0
        prompt = f"This will delete {len(names)} collections (" + ", ".join(names) + ") . Continue? [y/N]: "
        try:
            resp = input(prompt).strip().lower()
        except EOFError:
            resp = "n"
        if resp not in ("y", "yes"):
            logger.info("Aborted by user.")
            return 0

    try:
        delete_all_collections(client, dry_run=args.dry_run)
        return 0
    except Exception as e:
        logger.error("Error while deleting collections: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


