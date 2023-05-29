import os
import asyncio
import argparse
import pandas as pd
from ydata_profiling import ProfileReport
from settings import DB, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    MONGO_COLLECTION_LP_PACKET_INTEREST, MONGO_COLLECTION_LP_PACKET_DATA, LOGGER, DATA_DIR


class Profiler:
    def __init__(self, db, collections):
        self.db = db
        self.collections = collections

    async def get_profile(self, data_type):
        LOGGER.info('Getting the packets...')
        pipeline = [
            {'$project': {
                '_id': 0, 'ndn': '$_source.layers.ndn'}},
        ]
        if data_type == 'interest':
            collections = [self.collections['INTEREST'],
                           self.collections['LP_PACKET_INTEREST']]
        elif data_type == 'data':
            collections = [self.collections['DATA'],
                           self.collections['LP_PACKET_DATA']]

        d = []
        for collection in collections:
            r = self.db[collection].aggregate(pipeline)

            async for doc in r:
                if collection in [self.collections['LP_PACKET_INTEREST'], self.collections['LP_PACKET_DATA']]:
                    doc['ndn'] = doc['ndn'][1]
                d.append(doc['ndn'])

        LOGGER.info('Building the profile...')
        df = pd.DataFrame(d)
        sample_df = df.sample(frac=0.1)
        profile = ProfileReport(
            sample_df, title=f'{data_type} profile')
        profile.to_file(os.path.join(DATA_DIR, f'{data_type}_profile.html'))
        LOGGER.info(
            f'Profile saved to {os.path.join(DATA_DIR, f"{data_type}_profile.html")}')

        # Clean up
        del df
        del sample_df
        del profile


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Get packets profile', prog='python -m tools.profile')
    parser.add_argument("--data-type", help="Type of data to build profile for.", choices=[
                        'interest', 'data'], default='interest')
    args = parser.parse_args()

    profiler = Profiler(DB, {'INTEREST': MONGO_COLLECTION_INTEREST, 'DATA': MONGO_COLLECTION_DATA,
                             'LP_PACKET_INTEREST': MONGO_COLLECTION_LP_PACKET_INTEREST, 'LP_PACKET_DATA': MONGO_COLLECTION_LP_PACKET_DATA})
    asyncio.run(profiler.get_profile(args.data_type))
