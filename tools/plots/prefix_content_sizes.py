import asyncio
import argparse
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from settings import DB, LOGGER, MONGO_COLLECTION_DATA, \
    DATA_DIR, MONGO_DB_NAME


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
                name_components = packet['name'].split('/')[1:]

                for term in content_sizes.keys():
                    if any(term in comp for comp in name_components):
                        content_size = packet['size3']
                        content_sizes[term].append(content_size)

        LOGGER.info('Preparing data...')
        df = pd.DataFrame.from_dict(content_sizes, orient='index').transpose()

        LOGGER.info('Plotting...')
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.grid(axis='y')
        for column in df.columns:
            sns.histplot(df[column].dropna(), ax=ax)
            ax.set_xlabel('Data Packet Size [Bytes]', fontsize=30)
            ax.set_ylabel('Count', fontsize=30)
            ax.tick_params(axis='both', which='major', labelsize=28)
            ax.tick_params(axis='both', which='minor', labelsize=26)

        plt.tight_layout()

        if self.save_fig:
            fig.savefig(os.path.join(
                DATA_DIR, f'{MONGO_DB_NAME}-prefix_content_sizes.pdf'), bbox_inches='tight', dpi=300)
            LOGGER.info(
                f'Prefix content sizes saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-prefix_content_sizes.pdf")}')
        else:
            plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot prefixes to content sizes for data packets.', prog='python -m tools.plots.prefix_content_sizes')

    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = PrefixContentSizes(
        DB, {'DATA': MONGO_COLLECTION_DATA})

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
