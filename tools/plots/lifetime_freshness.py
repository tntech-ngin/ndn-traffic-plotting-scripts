import os
import asyncio
import argparse
import numpy as np
import matplotlib.pyplot as plt
from settings import DB, LOGGER, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    DATA_DIR, MONGO_DB_NAME


class LifetimeFreshnessCDF:
    DEFAULT_LIFETIME = 4000
    DEFAULT_FRESHNESS = 0

    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.save_fig = False

    async def plot(self):
        LOGGER.info('Getting the packets...')
        interest_lifetime_values = []
        data_freshness_values = []
        for collection_name, collection in self.collections.items():
            async for document in self.db[collection].find({}, {'lifetime': 1, 'freshness': 1, '_id': 0}):
                if collection_name == 'INTEREST':
                    interest_lifetime_values.append(
                        document.get('lifetime', LifetimeFreshnessCDF.DEFAULT_LIFETIME))
                elif collection_name == 'DATA':
                    if document.get('freshness'):
                        # data_freshness_values.append(
                        #     document.get('freshness', LifetimeFreshnessCDF.DEFAULT_FRESHNESS))
                        data_freshness_values.append(
                            document.get('freshness'))

        interest_lifetime_values.sort()
        data_freshness_values.sort()
        interest_lifetime_cdf = np.arange(
            1, len(interest_lifetime_values) + 1) / len(interest_lifetime_values)
        data_freshness_cdf = np.arange(
            1, len(data_freshness_values) + 1) / len(data_freshness_values)

        LOGGER.info('Plotting...')
        fig, ax1 = plt.subplots(figsize=(8, 4))
        ax1.plot(interest_lifetime_values, interest_lifetime_cdf,
                 label='Interest lifetime')
        ax1.plot(data_freshness_values, data_freshness_cdf,
                 label='Data freshness', color='r')
        ax1.set_xlim(0.5, 1e8)

        ax1.xaxis.label.set_size(10)
        ax1.yaxis.label.set_size(10)

        ax1.yaxis.set_minor_locator(plt.MultipleLocator(0.1))

        ax1.set_xscale('log')
        ax1.set_xlabel('Lifetime / Freshness (ms)')
        ax1.set_ylabel('CDF')
        ax1.legend(loc='upper left')

        fig.tight_layout()

        if self.save_fig:
            fig.savefig(os.path.join(DATA_DIR, f'{MONGO_DB_NAME}-lifetimefreshness-cdf.pdf'),
                        bbox_inches='tight')
            LOGGER.info(
                f'Lifetimefreshness cdf saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-lifetimefreshness-cdf.pdf")}')
        else:
            plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot interest lifetime cdf', prog='python -m tools.plots.lifetime_freshness')

    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = LifetimeFreshnessCDF(
        DB, {'INTEREST': MONGO_COLLECTION_INTEREST, 'DATA': MONGO_COLLECTION_DATA})

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
