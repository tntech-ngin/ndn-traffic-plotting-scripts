import os
import asyncio
import argparse
from matplotlib import cm, ticker
from datetime import datetime, timedelta
from ndn.encoding import Name
import matplotlib.pyplot as plt
import numpy as np
from settings import DB, LOGGER, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    DATA_DIR, MONGO_DB_NAME


class PacketsHistogram:
    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.save_fig = False

    async def plot(self, duration):
        LOGGER.info('Getting the packets...')
        i_ts = []
        d_ts = []
        for collection in self.collections.values():
            pipeline = [
                {'$project': {
                    '_id': 0, 'frame_time_epoch': 'frame_time_epoch'}},
                {'$sort': {'frame_time_epoch': 1}}
            ]
            r = self.db[collection].aggregate(pipeline)
            timestamps = []
            async for doc in r:
                timestamps.append(int(float(doc['frame_time_epoch']) * 1e9))

            if collection == self.collections['INTEREST']:
                i_ts = i_ts + timestamps if i_ts else timestamps
            elif collection == self.collections['DATA']:
                d_ts = d_ts + timestamps if d_ts else timestamps

        # count number of packets in each duration
        start_time = datetime.fromtimestamp(min(i_ts[0], d_ts[0]) / 1e9)
        end_time = datetime.fromtimestamp(max(i_ts[-1], d_ts[-1]) / 1e9)

        # floor start_time to nearest hour
        start_time = start_time.replace(
            minute=0, second=0, microsecond=0)
        # ceil end_time to nearest hour
        end_time = end_time.replace(
            minute=0, second=0, microsecond=0) + timedelta(hours=1)

        d = int((end_time - start_time).total_seconds())
        num_durations = d // (duration * 60) + 1

        LOGGER.info(f'Number of durations: {num_durations}')

        interest_num_packets = [0] * num_durations
        interest_ts = [0] * num_durations
        data_num_packets = [0] * num_durations
        data_ts = [0] * num_durations

        for packet_t in i_ts:
            packet_duration = int((datetime.fromtimestamp(
                packet_t / 1e9) - start_time).total_seconds() // (duration * 60))
            interest_num_packets[packet_duration] += 1
            interest_ts[packet_duration] = datetime.fromtimestamp(
                packet_t / 1e9)
        for packet_t in d_ts:
            packet_duration = int((datetime.fromtimestamp(
                packet_t / 1e9) - start_time).total_seconds() // (duration * 60))
            data_num_packets[packet_duration] += 1
            data_ts[packet_duration] = datetime.fromtimestamp(
                packet_t / 1e9)

        # plot
        fig, ax = plt.subplots(figsize=(12, 7))
        ax.bar(np.arange(num_durations), interest_num_packets,
               color=cm.Paired(0), label='Interest packets')
        ax.bar(np.arange(num_durations),
               data_num_packets, color=cm.Paired(1), label='Data packets', align='edge')
        duration_labels = [(start_time + timedelta(minutes=i * duration)).strftime('%-I %p')
                           for i in range(num_durations)]
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(
            lambda x, pos: duration_labels[int(x)] if x < len(duration_labels) else ''))

        ax.set_xlabel('Timestamp')
        ax.set_ylabel(f'Packets per {duration} minutes')
        ax.legend()

        if self.save_fig:
            fig.savefig(os.path.join(DATA_DIR, f'{MONGO_DB_NAME}-histogram-{duration}.pdf'),
                        bbox_inches='tight')
            LOGGER.info(
                f'Histogram saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-histogram-{duration}.pdf")}')

        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot packets histogram', prog='python -m tools.plots.components_hexbin')

    parser.add_argument('--duration', default=60, type=int,
                        help=f'Duration in minutes to group packets (default: 60)')
    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = PacketsHistogram(
        DB, {'INTEREST': MONGO_COLLECTION_INTEREST, 'DATA': MONGO_COLLECTION_DATA})

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
