import os
import asyncio
import argparse
import matplotlib.pyplot as plt
import numpy as np
from settings import DB, LOGGER, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    MONGO_COLLECTION_NACK, DATA_DIR, MONGO_DB_NAME


class PacketTypeDistribution:
    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.save_fig = False

    async def plot(self):
        r = {}
        for collection in self.collections.values():
            r[collection] = await self.db[collection].count_documents({})

        print(f'INTERESTS: {r[MONGO_COLLECTION_INTEREST]}')
        print(f'DATA: {r[MONGO_COLLECTION_DATA]}')
        print(f'NACKS: {r[MONGO_COLLECTION_NACK]}')

        # plot pie chart for packet type distribution
        fig, ax = plt.subplots(figsize=(12, 7))
        fig.suptitle('Packet type distribution', fontsize=16)

        def absolute_value(val):
            a = np.round(val/100.*np.sum([r[MONGO_COLLECTION_INTEREST],
                         r[MONGO_COLLECTION_DATA], r[MONGO_COLLECTION_NACK]]))
            return int(a)

        ax.pie([r[MONGO_COLLECTION_INTEREST], r[MONGO_COLLECTION_DATA], r[MONGO_COLLECTION_NACK]], labels=[
            'Interest', 'Data', 'Nack'], autopct=absolute_value, startangle=90)
        ax.axis('equal')
        ax.legend()

        if self.save_fig:
            plt.savefig(os.path.join(
                DATA_DIR, f'{MONGO_DB_NAME}-packet-type-distribution.pdf'), bbox_inches='tight')
            LOGGER.info(
                f'Packet type distribution saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-packet-type-distribution.pdf")}')

        plt.show()
        plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot NDN packet statistics.', prog='python -m tools.plots.packet-type-distribution')

    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = PacketTypeDistribution(DB, {'INTEREST': MONGO_COLLECTION_INTEREST, 'DATA': MONGO_COLLECTION_DATA,
                                       'LP_PACKET_NACK': MONGO_COLLECTION_NACK})

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
