import os
import asyncio
import argparse
from matplotlib import colors
from ndn.encoding import Name
import matplotlib.pyplot as plt
import numpy as np
from settings import DB, LOGGER, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    DATA_DIR, MONGO_DB_NAME


class ComponentsHexbin:
    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.save_fig = False

    async def plot(self):
        LOGGER.info('Getting the packets...')
        i_d = []
        d_d = []
        for collection in self.collections.values():
            async for document in self.db[collection].find({}, {'name': 1, '_id': 0}):
                n = document['name']
                num_c = len(n.split('/')) - 1
                try:
                    name_len = len(Name.to_bytes(n))
                except ValueError as e:
                    LOGGER.warning(f'Invalid name: {n}. Error: {e}')
                    continue

                if collection == self.collections['INTEREST']:
                    i_d.append((num_c, name_len))
                elif collection == self.collections['DATA']:
                    d_d.append((num_c, name_len))

        LOGGER.info('Plotting...')
        fig, ax = plt.subplots(figsize=(12, 7))
        ax.tick_params(axis='both', which='major', labelsize=9)
        hb1 = ax.hexbin(*zip(*i_d), gridsize=25, cmap='Blues',
                        alpha=0.9, mincnt=25, edgecolors='blue')
        hb2 = ax.hexbin(*zip(*d_d), gridsize=25, cmap='Oranges',
                        alpha=0.9, mincnt=25, edgecolors='orange')

        max_count = max(hb1.get_array().max(), hb2.get_array().max())
        min_count = min(hb1.get_array().min(), hb2.get_array().min())
        norm = colors.Normalize(vmin=min_count, vmax=max_count)

        hb1 = ax.hexbin(*zip(*i_d), gridsize=25, cmap='Blues', norm=norm,
                        alpha=0.9, mincnt=25, edgecolors='blue')
        hb2 = ax.hexbin(*zip(*d_d), gridsize=25, cmap='Oranges', norm=norm,
                        alpha=0.9, mincnt=25, edgecolors='orange')

        cb1 = fig.colorbar(hb1)
        cb1.set_label('Interest Frequency', fontsize=10)
        cb1.ax.tick_params(labelsize=9)
        cb2 = fig.colorbar(hb2)
        cb2.set_label('Data Frequency', fontsize=10)
        cb2.ax.tick_params(labelsize=9)

        ax.set_xlabel('Number of Components', fontsize=10)
        ax.set_ylabel('Name Length [Bytes]', fontsize=10)

        ax.grid(axis='y')
        ax.set_ylim(bottom=0)
        ax.yaxis.set_ticks(np.arange(0, ax.get_ylim()[1], 50))

        if self.save_fig:
            fig.savefig(os.path.join(DATA_DIR, f'{MONGO_DB_NAME}-hexbin.pdf'),
                        bbox_inches='tight')
            LOGGER.info(
                f'Hexbin saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-hexbin.pdf")}')
        else:
            plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot components distribution hexbin', prog='python -m tools.plots.components_hexbin')

    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = ComponentsHexbin(
        DB, {'INTEREST': MONGO_COLLECTION_INTEREST, 'DATA': MONGO_COLLECTION_DATA})

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
