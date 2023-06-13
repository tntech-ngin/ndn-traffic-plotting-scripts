import os
import asyncio
import json
import argparse
from tqdm import tqdm
from settings import DB, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    MONGO_COLLECTION_LP_PACKET_FRAG, MONGO_COLLECTION_LP_PACKET_NACK, \
    MONGO_COLLECTION_LP_PACKET_INTEREST, MONGO_COLLECTION_LP_PACKET_DATA, LOGGER


class Indexer:
    def __init__(self, db, batch_size=10000):
        self.db = db
        self.batch_size = batch_size
        self.bulk_data = {
            MONGO_COLLECTION_INTEREST: [],
            MONGO_COLLECTION_DATA: [],
            MONGO_COLLECTION_LP_PACKET_FRAG: [],
            MONGO_COLLECTION_LP_PACKET_NACK: [],
            MONGO_COLLECTION_LP_PACKET_INTEREST: [],
            MONGO_COLLECTION_LP_PACKET_DATA: [],
        }

    async def _index_packet(self, type, packet):
        self.bulk_data[type].append(packet)

        # If the batch is filled, perform bulk inserts
        if len(self.bulk_data[type]) == self.batch_size:
            await self.db[type].insert_many(self.bulk_data[type])
            self.bulk_data[type] = []

    def packets_generator(self, file_path):
        with open(file_path, 'r') as file:
            for line in file:
                yield json.loads(line)

    async def index_json(self, file_path):
        progress_bar = tqdm(desc='Indexing packets', unit=' packet')

        for packet in self.packets_generator(file_path):
            try:
                ndn_layer = packet['_source']['layers']['ndn']
            except KeyError:
                # LOGGER.error(f'Error: The packet {packet} does not contain NDN layer')
                continue
            if 'ndn_interest' in ndn_layer:
                await self._index_packet(MONGO_COLLECTION_INTEREST, packet)
            elif 'ndn_data' in ndn_layer:
                await self._index_packet(MONGO_COLLECTION_DATA, packet)
            # elif 'ndn_lp_packet' in ndn_layer:
            #     await self._index_packet(MONGO_COLLECTION_LP_PACKET_FRAG, packet)
            elif type(ndn_layer) is list:
                if 'ndn_nack' in ndn_layer[0]:
                    await self._index_packet(
                        MONGO_COLLECTION_LP_PACKET_NACK, packet)
                elif 'ndn_interest' in ndn_layer[1]:
                    await self._index_packet(
                        MONGO_COLLECTION_LP_PACKET_INTEREST, packet)
                elif 'ndn_data' in ndn_layer[1]:
                    await self._index_packet(
                        MONGO_COLLECTION_LP_PACKET_DATA, packet)

            progress_bar.update()

        # Perform reamining bulk inserts if any document is left
        for collection, data in self.bulk_data.items():
            if data:
                await self.db[collection].insert_many(data)

        LOGGER.info('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Index JSON file into MongoDB.", prog='python -m tools.index')
    parser.add_argument("file_path", help="Path to JSON file.")
    args = parser.parse_args()

    if not os.path.exists(args.file_path):
        LOGGER.error(f"Error: The file {args.file_path} does not exist.")
        exit(1)

    indexer = Indexer(DB)
    asyncio.run(indexer.index_json(args.file_path))
