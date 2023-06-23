import os
import asyncio
import argparse
from matplotlib import ticker
import matplotlib.pyplot as plt
from settings import DB, LOGGER, MONGO_COLLECTION_INTEREST, DATA_DIR, MONGO_DB_NAME


class HopLimit:
    DEFAULT_HOPLIMIT = 255

    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.save_fig = False

    async def plot(self):
        LOGGER.info('Getting packets....')
        hoplimits = []
        for _, collection in self.collections.items():
            async for document in self.db[collection].find({}, {'hopLimit': 1, '_id': 0}):
                if document.get('hopLimit'):
                    # hoplimits.append(document.get('hopLimit', HopLimit.DEFAULT_HOPLIMIT))
                    hoplimits.append(document.get('hopLimit'))

        counts = {}
        for hoplimit in hoplimits:
            counts[hoplimit] = counts.get(hoplimit, 0) + 1

        LOGGER.info('Plotting...')
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.bar(counts.keys(), counts.values())
        ax.set_xlabel('Hop Limit', fontsize=30)
        ax.set_ylabel('Count', fontsize=30)
        ax.set_xlim(-5, 260)  # Margins of 5
        ax.set_ylim(bottom=0)
        ax.set_yscale('symlog')
        ax.xaxis.set_major_locator(ticker.MultipleLocator(25))
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(12.5))
        ax.grid(axis='y')

        ax.tick_params(axis='both', which='major', labelsize=28)
        ax.tick_params(axis='both', which='minor', labelsize=26)

        fig.tight_layout()

        if self.save_fig:
            fig.savefig(os.path.join(
                DATA_DIR, f'{MONGO_DB_NAME}-hoplimit.pdf'), bbox_inches='tight', dpi=300)
            LOGGER.info(
                f'Hop limit saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-hoplimit.pdf")}')
        else:
            plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot hop limit CDF', prog='python -m tools.plots.hoplimit')

    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = HopLimit(DB, {'INTEREST': MONGO_COLLECTION_INTEREST})

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
