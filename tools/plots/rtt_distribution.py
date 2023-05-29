import os
import asyncio
import argparse
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
from settings import DB, LOGGER, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    MONGO_COLLECTION_LP_PACKET_INTEREST, MONGO_COLLECTION_LP_PACKET_DATA, \
    MONGO_DB_NAME, DATA_DIR


class RTTDistribution:
    CAN_BE_PREFIX = 'Yes'

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
            pipeline = {'_id': 0, '_source.layers.frame.frame_time_epoch': 1,
                        '_source.layers.ndn.ndn_name': 1}

            LOGGER.info('Getting the packets...')
            for collection in self.collections.values():
                async for packet in self.db[collection].find({}, pipeline).sort('_source.layers.frame.frame_time_epoch', 1):
                    packet_time = int(
                        float(packet['_source']['layers']['frame']['frame_time_epoch']) * 1e9)
                    packet_name = packet['_source']['layers']['ndn']['ndn_name'] if collection in [
                        self.collections['INTEREST'], self.collections['DATA']] else packet['_source']['layers']['ndn'][1]['ndn_name']

                    if collection in [self.collections['INTEREST'], self.collections['LP_PACKET_INTEREST']]:
                        can_be_prefix = packet['_source']['layers']['ndn'].get('ndn_canbeprefix') == RTTDistribution.CAN_BE_PREFIX if collection == self.collections[
                            'INTEREST'] else packet['_source']['layers']['ndn'][1].get('ndn_canbeprefix') == RTTDistribution.CAN_BE_PREFIX
                        i_p[packet_name] = {
                            'time': packet_time, 'can_be_prefix': can_be_prefix}

                    elif collection in [self.collections['DATA'], self.collections['LP_PACKET_DATA']]:
                        d_p[packet_name] = packet_time

            # make sure that the interest and data packets are sorted by time
            i_p = dict(sorted(i_p.items(), key=lambda item: item[1]['time']))
            d_p = dict(sorted(d_p.items(), key=lambda item: item[1]))

            # for each interest packet, find the nearest data packet that starts with the same name or has same interest prefix
            # and calculate the RTT
            LOGGER.info('Finding RTTs...')
            rtt = []
            progress_bar = tqdm(
                total=len(d_p), desc='Finding RTTs', unit='packet')
            for data_name, data_time in d_p.items():
                for interest_name, interest_info in i_p.items():
                    interest_time = interest_info['time']

                    if interest_time > data_time:
                        break

                    interest_can_be_prefix = interest_info['can_be_prefix'] == RTTDistribution.CAN_BE_PREFIX

                    if (not interest_can_be_prefix and interest_name == data_name) or (interest_can_be_prefix and data_name.starts_with(interest_name)):
                        rtt.append(data_time - interest_time)
                        del i_p[interest_name]
                        break

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
                f'Histogram saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-rtt-distribution.pdf")}')
        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot NDN packet statistics.', prog='python -m tools.plots.rtt_distribution')

    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = RTTDistribution(DB, {'INTEREST': MONGO_COLLECTION_INTEREST, 'DATA': MONGO_COLLECTION_DATA,
                                'LP_PACKET_INTEREST': MONGO_COLLECTION_LP_PACKET_INTEREST, 'LP_PACKET_DATA': MONGO_COLLECTION_LP_PACKET_DATA})
    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
