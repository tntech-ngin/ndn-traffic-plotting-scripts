import asyncio
import argparse
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import seaborn as sns
from settings import *


class PrefixContentSizes:
    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.save_fig = False

    async def plot(self):
        search_terms = ['nlsr']
        content_sizes = {term: [] for term in search_terms}

        LOGGER.info('Getting the packets...')
        for collection in self.collections.values():
            async for packet in self.db[collection].find({}, {'_id': 0, 'name': 1, 'size3': 1}):
                for term in search_terms:
                    if term in packet['name']:
                        content_sizes[term].append(packet['size3'])

        LOGGER.info('Preparing data...')
        df = pd.DataFrame.from_dict(content_sizes, orient='index').transpose()

        LOGGER.info('Plotting...')
        sns.set_context('paper', font_scale=2)
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.grid(axis='y')
        for column in df.columns:
            sns.histplot(df[column].dropna(), ax=ax)
            ax.set_xlabel('Data Packet Size [Bytes]')
            ax.set_ylabel('Count')
            ax.tick_params(axis='both', which='major')
            ax.tick_params(axis='both', which='minor')

        plt.tight_layout()

        if self.save_fig:
            fig.savefig(os.path.join(
                DATA_DIR, f'{MONGO_DB_NAME}-content_size_distribution.pdf'), bbox_inches='tight', dpi=300)
            LOGGER.info(
                f'Content size distribution saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-content_size_distribution.pdf")}')
        else:
            plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot content size distribution for data packets.', prog='python -m tools.plots.content_size_distribution')

    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = PrefixContentSizes(
        DB, {'DATA': MONGO_COLLECTION_DATA})

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
