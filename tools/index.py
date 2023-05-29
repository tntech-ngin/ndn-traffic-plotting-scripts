import os
import json
import argparse
from tqdm import tqdm
from settings import DB, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    MONGO_COLLECTION_LP_PACKET_FRAG, MONGO_COLLECTION_LP_PACKET_NACK, \
    MONGO_COLLECTION_LP_PACKET_INTEREST, MONGO_COLLECTION_LP_PACKET_DATA, LOGGER


class Indexer:
    def __init__(self, db):
        self.db = db

    def _index_packet(self, type, packet):
        self.db[type].insert_one(packet)

    def index_json(self, file_path):
        with open(file_path) as json_file:
            progress_bar = tqdm(desc='Indexing packets', unit=' packet')

            for line in json_file:
                packet = json.loads(line)
                try:
                    ndn_layer = packet['_source']['layers']['ndn']
                except KeyError:
                    # LOGGER.error(f'Error: The packet {packet} does not contain NDN layer')
                    continue
                if 'ndn_interest' in ndn_layer:
                    self._index_packet(MONGO_COLLECTION_INTEREST, packet)
                elif 'ndn_data' in ndn_layer:
                    self._index_packet(MONGO_COLLECTION_DATA, packet)
                elif 'ndn_lp_packet' in ndn_layer:
                    self._index_packet(MONGO_COLLECTION_LP_PACKET_FRAG, packet)
                elif type(ndn_layer) is list:
                    if 'ndn_nack' in ndn_layer[0]:
                        self._index_packet(
                            MONGO_COLLECTION_LP_PACKET_NACK, packet)
                    elif 'ndn_interest' in ndn_layer[1]:
                        self._index_packet(
                            MONGO_COLLECTION_LP_PACKET_INTEREST, packet)
                    elif 'ndn_data' in ndn_layer[1]:
                        self._index_packet(
                            MONGO_COLLECTION_LP_PACKET_DATA, packet)

                progress_bar.update()

        json_file.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Index JSON file into MongoDB.", prog='python -m tools.index')
    parser.add_argument("file_path", help="Path to JSON file.")
    args = parser.parse_args()

    if not os.path.exists(args.file_path):
        LOGGER.error(f"Error: The file {args.file_path} does not exist.")
        exit(1)

    indexer = Indexer(DB)
    indexer.index_json(args.file_path)
