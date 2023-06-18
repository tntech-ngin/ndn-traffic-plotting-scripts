import os
import asyncio
import argparse
from matplotlib import cm, ticker
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
from settings import DB, LOGGER, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    MONGO_COLLECTION_NACK, MONGO_COLLECTION_FRAGMENT, \
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
        r_ts = []
        i_sizes = []
        d_sizes = []
        r_sizes = []
        for collection in self.collections.values():
            pipeline = [
                {'$project': {
                    '_id': 0, 'ts': 1, 'size2': 1}},
                {'$sort': {'ts': 1}},
            ]
            r = self.db[collection].aggregate(pipeline)
            sizes = []
            async for doc in r:
                if collection == self.collections['INTEREST']:
                    i_ts.append(doc['ts'])
                    i_sizes.append(doc['size2'])
                elif collection == self.collections['DATA']:
                    d_ts.append(doc['ts'])
                    d_sizes.append(doc['size2'])
                else:
                    r_ts.append(doc['ts'])
                    r_sizes.append(doc['size2'])
                sizes.append(doc['size2'])

        LOGGER.info('Preparing the data...')
        # Calculate number of packets / bytes in each duration
        start_time = datetime.utcfromtimestamp(min(i_ts[0], d_ts[0]) / 1e9)
        end_time = datetime.utcfromtimestamp(max(i_ts[-1], d_ts[-1]) / 1e9)

        d = int((end_time - start_time).total_seconds())
        num_durations = d // (duration * 60) + 1
        if num_durations > 3 * 60 // duration:
            num_durations = 3 * 60 // duration

        interest_num_packets = [0] * num_durations
        interest_ts = [0] * num_durations
        data_num_packets = [0] * num_durations
        data_ts = [0] * num_durations
        interest_throughput = [0] * num_durations
        data_throughput = [0] * num_durations
        r_throughput = [0] * num_durations

        for packet_t, size in zip(i_ts, i_sizes):
            packet_duration = int((datetime.utcfromtimestamp(
                packet_t / 1e9) - start_time).total_seconds() // (duration * 60))
            packet_duration = min(packet_duration, num_durations-1)
            interest_num_packets[packet_duration] += 1
            interest_ts[packet_duration] = datetime.utcfromtimestamp(
                packet_t / 1e9)
            interest_throughput[packet_duration] += size
        for packet_t, size in zip(d_ts, d_sizes):
            packet_duration = int((datetime.utcfromtimestamp(
                packet_t / 1e9) - start_time).total_seconds() // (duration * 60))
            packet_duration = min(packet_duration, num_durations-1)
            data_num_packets[packet_duration] += 1
            data_ts[packet_duration] = datetime.utcfromtimestamp(
                packet_t / 1e9)
            data_throughput[packet_duration] += size
        for packet_t, size in zip(r_ts, r_sizes):
            packet_duration = int((datetime.utcfromtimestamp(
                packet_t / 1e9) - start_time).total_seconds() // (duration * 60))
            packet_duration = min(packet_duration, num_durations-1)
            r_throughput[packet_duration] += size

        throughput = [0] * num_durations
        for i in range(num_durations):
            throughput[i] = interest_throughput[i] + \
                data_throughput[i] + r_throughput[i]
        throughput = [t * 8 / (duration * 60) / 1e6 for t in throughput]

        LOGGER.info('Plotting...')
        fig, ax = plt.subplots(figsize=(12, 7))
        ax.bar(np.arange(num_durations), interest_num_packets,
               color=cm.Paired(0), label='Interests', align='edge')
        ax.bar(np.arange(num_durations),
               data_num_packets, color=cm.Paired(1), label='Data', align='edge')
        duration_labels = [(start_time + timedelta(minutes=i * duration)).strftime('%-I:%M %p')
                           for i in range(num_durations + 1)]

        ax.xaxis.set_major_locator(
            ticker.MultipleLocator(min(30/duration, num_durations)))
        ax.xaxis.set_minor_locator(
            ticker.MultipleLocator(min(15/duration, num_durations)))
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(
            lambda x, pos: duration_labels[int(x)] if x < len(duration_labels) else ''))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(200000))
        formatter = ticker.ScalarFormatter(useMathText=True)
        formatter.set_powerlimits((-3, 3))
        ax.yaxis.set_major_formatter(formatter)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(
            lambda x, pos: '0' if x == 0 else f'{x:.0e}'.replace('e+', 'e').replace('e0', 'e')))

        ax.set_xlabel('Timestamp (UTC)')
        ax.set_ylabel(f'Packets per {duration} minutes')
        ax.legend()

        ax2 = ax.twinx()
        # ax2.plot(np.arange(num_durations) + 0.5, throughput,
        #          color='r', linestyle='-', marker='o')
        ax2.plot(np.arange(num_durations) + 0.5, throughput,
                 color='r', linestyle='-')
        ax2.set_ylabel('Throughput (Mbps)')
        ax2.yaxis.set_major_locator(ticker.MultipleLocator(10))
        ax2.set_ylim(bottom=0)

        if self.save_fig:
            fig.savefig(os.path.join(DATA_DIR, f'{MONGO_DB_NAME}-histogram-{duration}.pdf'),
                        bbox_inches='tight')
            LOGGER.info(
                f'Histogram saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-histogram-{duration}.pdf")}')
        else:
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
        DB, {'INTEREST': MONGO_COLLECTION_INTEREST, 'DATA': MONGO_COLLECTION_DATA, 'NACK': MONGO_COLLECTION_NACK, 'FRAGMENT': MONGO_COLLECTION_FRAGMENT})

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot(args.duration))