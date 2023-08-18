import asyncio
import argparse
from matplotlib import ticker
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import PurePath
from settings import *


class LifetimeFreshnessCDF:
    DEFAULT_LIFETIME = 4000
    DEFAULT_FRESHNESS = 0

    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.output = False

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
        sns.set_context('paper', font_scale=2)
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.plot(interest_lifetime_values, interest_lifetime_cdf,
                label='Interest lifetime')
        ax.plot(data_freshness_values, data_freshness_cdf,
                label='Freshness period', color='r')
        ax.set_xlim(0.5, 1e8)
        ax.set_ylim(0, 1)
        ax.set_xscale('log')
        ax.set_xlabel('Lifetime / Freshness period [ms]')
        ax.set_ylabel('CDF')
        ax.grid(True)
        ax.legend(loc='upper left')
        ax.xaxis.set_minor_locator(ticker.LogLocator(
            base=10, subs=np.arange(1, 10.0), numticks=10))
        # ax.set_yticks(np.linspace(0, 1, num=11))
        ax.yaxis.set_minor_locator(plt.MultipleLocator(0.1))
        ax.tick_params(axis='both', which='major')
        ax.tick_params(axis='both', which='minor')
        fig.tight_layout()

        if self.output:
            filename = PurePath(self.output).with_suffix('.pdf')
            fig.savefig(filename, bbox_inches='tight', dpi=300)
            LOGGER.info(
                f'Lifetimefreshness cdf saved to {f"{filename}"}')
        else:
            plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot interest lifetime cdf', prog='python -m tools.plots.lifetime_freshness')
    parser.add_argument('-o', '--output', metavar='FILE',
                        type=str, help='Save to file.')
    args = parser.parse_args()

    plot = LifetimeFreshnessCDF(
        DB, {'INTEREST': MONGO_COLLECTION_INTEREST, 'DATA': MONGO_COLLECTION_DATA})

    plot.output = args.output
    asyncio.run(plot.plot())
