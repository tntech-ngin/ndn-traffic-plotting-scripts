import os
import aiohttp
from settings import DB, LOGGER, MONGO_COLLECTION_DATA, MONGO_COLLECTION_LP_PACKET_DATA, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_LP_PACKET_INTEREST, DATA_DIR
from datetime import datetime, timedelta
from matplotlib import cm, ticker
import matplotlib.pyplot as plt
import numpy as np

routes_plots = aiohttp.web.RouteTableDef()


@routes_plots.get('/interest-to-data/')
async def interest_to_data(request):
    collections = [MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA,
                   MONGO_COLLECTION_LP_PACKET_INTEREST, MONGO_COLLECTION_LP_PACKET_DATA]
    i_ts = []
    d_ts = []
    for collection in collections:
        pipeline = [
            {'$project': {
                '_id': 0, 'frame_time_epoch': '$_source.layers.frame.frame_time_epoch'}},
            {'$sort': {'frame_time_epoch': 1}}
        ]
        r = DB[collection].aggregate(pipeline)
        timestamps = []
        async for doc in r:
            timestamps.append(int(float(doc['frame_time_epoch']) * 1e9))

        if collection == MONGO_COLLECTION_INTEREST:
            i_ts = i_ts + timestamps if i_ts else timestamps
        elif collection == MONGO_COLLECTION_DATA:
            d_ts = d_ts + timestamps if d_ts else timestamps
        elif collection == MONGO_COLLECTION_LP_PACKET_INTEREST:
            i_ts = i_ts + timestamps if i_ts else timestamps
        elif collection == MONGO_COLLECTION_LP_PACKET_DATA:
            d_ts = d_ts + timestamps if d_ts else timestamps

    # count number of packets in each duration
    duration = 60
    start_time = datetime.fromtimestamp(min(i_ts[0], d_ts[0]) / 1e9)
    end_time = datetime.fromtimestamp(max(i_ts[-1], d_ts[-1]) / 1e9)
    d = int((end_time - start_time).total_seconds())
    num_durations = d // (duration * 60) + 1

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

    
    # count interest to data ratio in each duration
    interest_to_data_ratio = [0] * num_durations
    for i in range(num_durations):
        if data_num_packets[i] == 0:
            interest_to_data_ratio[i] = 0
        else:
            interest_to_data_ratio[i] = interest_num_packets[i] / data_num_packets[i]

    # plot
    fig, ax = plt.subplots(figsize=(12, 7))
    rshift = 1
    ax.bar(np.arange(num_durations) + rshift / 2, interest_to_data_ratio,
            color=cm.Paired(0), label='Interest to Data')
    duration_labels = [(start_time + timedelta(minutes=i * duration)).strftime('%-I %p')
                        for i in range(num_durations + rshift)]
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, pos: duration_labels[int(x)] if x < len(duration_labels) else ''))

    ax.set_xlabel('Timestamp')
    ax.set_ylabel(f'Packets per {duration} minutes')
    ax.legend()

    # if save_fig:
    #     fig.savefig(os.path.join(DATA_DIR, f'histogram-{duration}.pdf'),
    #                 bbox_inches='tight')
    #     LOGGER.info(
    #         f'Histogram saved to {os.path.join(DATA_DIR, f"histogram-{duration}.pdf")}')
