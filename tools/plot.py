import os
import asyncio
import argparse
from datetime import datetime, timedelta
from matplotlib import cm, ticker
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from ndn.encoding import Name
from settings import DB, LOGGER, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    MONGO_COLLECTION_LP_PACKET_INTEREST, MONGO_COLLECTION_LP_PACKET_DATA, DATA_DIR, MONGO_DB_NAME


class Plot:
    PACKETS_HISTOGRAM = 'packets_histogram'
    COMPONENTS_HEXBIN = 'components_hexbin'
    COMPONENTS_CDF = 'components_cdf'

    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.save_fig = False

    async def _components_hexbin(self):
        i_d = []
        d_d = []
        pipeline = [{'$project': {'_id': 0, '_source.layers.ndn': 1}}]
        for collection in self.collections.values():
            async for document in self.db[collection].aggregate(pipeline):
                if collection in [self.collections['INTEREST'], self.collections['DATA']]:
                    n = document['_source']['layers']['ndn']['ndn_name']
                    num_c = len(n.split('/')) - 1
                    name_len = len(Name.to_bytes(n))
                    if collection == self.collections['INTEREST']:
                        i_d.append((num_c, name_len))
                    else:
                        d_d.append((num_c, name_len))
                elif collection in [self.collections['LP_PACKET_INTEREST'], self.collections['LP_PACKET_DATA']]:
                    n = document['_source']['layers']['ndn'][1]['ndn_name']
                    num_c = len(n.split('/')) - 1
                    name_len = len(Name.to_bytes(n))
                    if collection == self.collections['LP_PACKET_INTEREST']:
                        i_d.append((num_c, name_len))
                    else:
                        d_d.append((num_c, name_len))

        fig, ax = plt.subplots(figsize=(12, 7))
        hb1 = ax.hexbin(*zip(*i_d), gridsize=25, cmap='Blues',
                        alpha=0.9, mincnt=25, edgecolors='blue')
        hb2 = ax.hexbin(*zip(*d_d), gridsize=25, cmap='Oranges',
                        alpha=0.9, mincnt=25, edgecolors='orange')

        cb1 = fig.colorbar(hb1)
        cb1.set_label('Interest Frequency', fontsize=12)
        cb2 = fig.colorbar(hb2)
        cb2.set_label('Data Frequency', fontsize=12)

        ax.set_xlabel('Number of Components', fontsize=12)
        ax.set_ylabel('Name Length (Bytes)', fontsize=12)

        ax.grid(axis='y')
        ax.set_ylim(bottom=0)
        ax.yaxis.set_ticks(np.arange(0, ax.get_ylim()[1], 50))

        if self.save_fig:
            fig.savefig(os.path.join(DATA_DIR, f'{MONGO_DB_NAME}-hexbin.pdf'),
                        bbox_inches='tight')
            LOGGER.info(
                f'Hexbin saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-hexbin.pdf")}')

        plt.show()

    async def _components_cdf(self):
        i_num_components = []
        d_num_components = []

        pipeline = [{'$project': {'_id': 0, '_source.layers.ndn': 1}}]
        for collection in self.collections.values():
            async for document in self.db[collection].aggregate(pipeline):
                if collection in [self.collections['INTEREST'], self.collections['DATA']]:
                    n = document['_source']['layers']['ndn']['ndn_name']
                    num_c = len(n.split('/')) - 1
                    if collection == self.collections['INTEREST']:
                        i_num_components.append(num_c)
                    else:
                        d_num_components.append(num_c)
                elif collection in [self.collections['LP_PACKET_INTEREST'], self.collections['LP_PACKET_DATA']]:
                    n = document['_source']['layers']['ndn'][1]['ndn_name']
                    num_c = len(n.split('/')) - 1
                    if collection == self.collections['LP_PACKET_INTEREST']:
                        i_num_components.append(num_c)
                    else:
                        d_num_components.append(num_c)

        i_counts, i_bin_edges = np.histogram(
            i_num_components, bins=np.arange(1, max(i_num_components)+1))
        i_cdf = np.cumsum(i_counts)
        i_cdf = i_cdf / i_cdf[-1]

        d_counts, d_bin_edges = np.histogram(
            d_num_components, bins=np.arange(1, max(d_num_components)+1))
        d_cdf = np.cumsum(d_counts)
        d_cdf = d_cdf / d_cdf[-1]

        fig, axs = plt.subplots(1, 2, figsize=(12, 7))

        axs[0].plot(i_bin_edges[:-1], i_cdf, label='Interest', color='blue')
        axs[0].set_xlabel('Number of Components', fontsize=12)
        axs[0].set_ylabel('Percentile', fontsize=12)
        axs[0].set_title('Interest', fontsize=12)
        axs[0].grid(axis='y')

        axs[1].plot(d_bin_edges[:-1], d_cdf, label='Data', color='orange')
        axs[1].set_xlabel('Number of Components', fontsize=12)
        axs[1].set_ylabel('Percentile', fontsize=12)
        axs[1].set_title('Data', fontsize=12)
        axs[1].grid(axis='y')

        plt.tight_layout()

        if self.save_fig:
            fig.savefig(os.path.join(DATA_DIR, f'{MONGO_DB_NAME}-cdf.pdf'),
                        bbox_inches='tight')
            LOGGER.info(
                f'CDF saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-cdf.pdf")}')

        plt.show()

    async def _packets_histogram(self, duration):
        i_ts = []
        d_ts = []
        for collection in self.collections.values():
            pipeline = [
                {'$project': {
                    '_id': 0, 'frame_time_epoch': '$_source.layers.frame.frame_time_epoch'}},
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
            elif collection == self.collections['LP_PACKET_INTEREST']:
                i_ts = i_ts + timestamps if i_ts else timestamps
            elif collection == self.collections['LP_PACKET_DATA']:
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

    async def plot(self, plot_type, duration):
        if plot_type == Plot.PACKETS_HISTOGRAM:
            await self._packets_histogram(duration)
        elif plot_type == Plot.COMPONENTS_HEXBIN:
            await self._components_hexbin()
        elif plot_type == Plot.COMPONENTS_CDF:
            await self._components_cdf()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot NDN packet statistics.', prog='python -m tools.plot')

    parser.add_argument('--plot_type', default='packets_histogram',
                        choices=[Plot.PACKETS_HISTOGRAM,
                                 Plot.COMPONENTS_HEXBIN, Plot.COMPONENTS_CDF],
                        help=f'Select plot type from {", ".join([Plot.PACKETS_HISTOGRAM, Plot.COMPONENTS_HEXBIN, Plot.COMPONENTS_CDF])} (default: {Plot.PACKETS_HISTOGRAM})')
    parser.add_argument('--duration', default=10, type=int,
                        help=f'Duration in minutes to group packets (default: 60) (applicable only for {Plot.PACKETS_HISTOGRAM} plot)')
    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    if args.plot_type == Plot.PACKETS_HISTOGRAM and args.duration <= 0:
        LOGGER.error(
            f'Error: Invalid duration provided for {args.plot_type} plot')
        exit(1)

    plot = Plot(DB, {'INTEREST': MONGO_COLLECTION_INTEREST, 'DATA': MONGO_COLLECTION_DATA,
                     'LP_PACKET_INTEREST': MONGO_COLLECTION_LP_PACKET_INTEREST, 'LP_PACKET_DATA': MONGO_COLLECTION_LP_PACKET_DATA})

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot(args.plot_type, args.duration))
