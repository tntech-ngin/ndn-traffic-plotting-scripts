import argparse
import asyncio
import json
import os

from tqdm import tqdm

from settings import (
    DB,
    LOGGER,
    MONGO_COLLECTION_DATA,
    MONGO_COLLECTION_FRAGMENT,
    MONGO_COLLECTION_INTEREST,
    MONGO_COLLECTION_NACK,
)


class Indexer:
    def __init__(self, db, batch_size=10000):
        self.db = db
        self.batch_size = batch_size
        self.bulk_data = {
            MONGO_COLLECTION_INTEREST: [],
            MONGO_COLLECTION_DATA: [],
            MONGO_COLLECTION_NACK: [],
            MONGO_COLLECTION_FRAGMENT: [],
        }

    async def _index_packet(self, type, packet):
        self.bulk_data[type].append(packet)

        # If the batch is filled, perform bulk inserts
        if len(self.bulk_data[type]) == self.batch_size:
            await self.db[type].insert_many(self.bulk_data[type])
            self.bulk_data[type] = []

    def packets_generator(self, file_path):
        with open(file_path) as file:
            for line in file:
                yield json.loads(line)

    async def index_json(self, file_path):
        progress_bar = tqdm(desc="Indexing packets", unit=" packet")

        for packet in self.packets_generator(file_path):
            packet_type = packet["t"]
            if "I" in packet_type:
                await self._index_packet(MONGO_COLLECTION_INTEREST, packet)
            elif "D" in packet_type:
                await self._index_packet(MONGO_COLLECTION_DATA, packet)
            elif "N" in packet_type:
                await self._index_packet(MONGO_COLLECTION_NACK, packet)
            else:
                await self._index_packet(MONGO_COLLECTION_FRAGMENT, packet)

            progress_bar.update()

        # Perform remaining bulk inserts if any document is left
        for collection, data in self.bulk_data.items():
            if data:
                await self.db[collection].insert_many(data)

        LOGGER.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Index JSON file into MongoDB.", prog="python -m tools.index"
    )
    parser.add_argument("file_path", help="Path to JSON file.")
    args = parser.parse_args()

    if not os.path.exists(args.file_path):
        LOGGER.error(f"Error: The file {args.file_path} does not exist.")
        exit(1)

    indexer = Indexer(DB)
    asyncio.run(indexer.index_json(args.file_path))
