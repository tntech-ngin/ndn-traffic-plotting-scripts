import os
import asyncio
import argparse
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
from settings import DB, LOGGER, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    MONGO_DB_NAME, DATA_DIR


class RTTDistribution:
    DEFAULT_LIFETIME = 4000 * 1e6

    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.save_fig = False

    async def plot(self):
        # If saved RTTs file exists, load it
        if os.path.exists(os.path.join(DATA_DIR, f'{MONGO_DB_NAME}-rtt-distribution.txt')):
            with open(os.path.join(DATA_DIR, f'{MONGO_DB_NAME}-rtt-distribution.txt'), 'r') as f:
                rtt = [int(line.strip()) for line in f.readlines()]

        else:
            i_p = {}
            d_p = {}
            pipeline = {
                '_id': 0,
                'frame_time_epoch': 1,
                'ndn_name': 1
            }

            LOGGER.info('Getting the packets...')
            for collection in self.collections.values():
                async for packet in self.db[collection].find({}, pipeline).sort('frame_time_epoch', 1):
                    packet_time = int(float(packet['frame_time_epoch']) * 1e9)
                    packet_name = packet['ndn_name']

                    if collection == self.collections['INTEREST']:
                        lifetime = packet['ndn_interestlifetime'] if 'ndn_interestlifetime' in packet else None
                        lifetime = (
                            int(lifetime) * 1e6) if lifetime else RTTDistribution.DEFAULT_LIFETIME
                        if packet_name in i_p:
                            i_p[packet_name].append({
                                'time': packet_time, 'lifetime': lifetime})
                        else:
                            i_p[packet_name] = [{
                                'time': packet_time, 'lifetime': lifetime}]

                    elif collection == self.collections['DATA']:
                        if packet_name in d_p:
                            d_p[packet_name].append(packet_time)
                        else:
                            d_p[packet_name] = [packet_time]

            # make sure that the interest and data packets are sorted by time
            i_p = dict(sorted(i_p.items(), key=lambda item: item[1]['time']))
            d_p = dict(sorted(d_p.items(), key=lambda item: item[1]))

            # for each data packet, find the nearest interest packet
            # and calculate the RTT
            LOGGER.info('Finding RTTs...')
            rtt = []
            progress_bar = tqdm(
                total=len(d_p), desc='Finding RTTs', unit='packet')
            for data_name, data_times in d_p.items():
                if data_name in i_p:
                    for data_time in data_times:
                        interest_packets = i_p[data_name]
                        interest_packet = None
                        for packet in reversed(interest_packets):
                            if packet['time'] < data_time and data_time < packet['time'] + packet['lifetime']:
                                interest_packet = packet
                                break

                        if interest_packet:
                            rtt.append(data_time - interest_packet['time'])
                            interest_packets.remove(interest_packet)

                progress_bar.update()
            progress_bar.close()

            with open(os.path.join(DATA_DIR, f'{MONGO_DB_NAME}-rtt-distribution.txt'), 'w') as f:
                f.write('\n'.join([str(r) for r in rtt]))
                LOGGER.info(
                    f'RTTs saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-rtt-distribution.txt")}')

        LOGGER.info('Plotting RTT CDF...')
        # Convert to milliseconds
        rtt = [r / 1e6 for r in rtt]
        sorted_rtt = np.sort(rtt)
        cumulative = np.cumsum(sorted_rtt) / np.sum(sorted_rtt)

        fig, ax = plt.subplots(figsize=(12, 7))
        ax.plot(sorted_rtt, cumulative, color='#0504aa')
        ax.set_xlabel('RTT (ms)', labelpad=10)
        ax.set_ylabel('CDF', labelpad=5)
        ax.set_title('RTT Cumulative Distribution')

        if self.save_fig:
            fig.savefig(os.path.join(DATA_DIR, f'{MONGO_DB_NAME}-rtt-distribution.pdf'),
                        bbox_inches='tight')
            LOGGER.info(
                f'RTTs saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-rtt-distribution.pdf")}')
        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot NDN packet statistics.', prog='python -m tools.plots.rtt_distribution')

    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = RTTDistribution(
        DB, {'INTEREST': MONGO_COLLECTION_INTEREST, 'DATA': MONGO_COLLECTION_DATA})
    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
