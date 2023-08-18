import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import PurePath

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib import ticker

from settings import *

# may 31
DBS = [
    "suns-cs-ucla-edu-2023-06-01T05:00:02Z",
    "wundngw-2023-06-01T05:00:20Z",
    "hobo-2023-06-01T05:00:03Z",
    "titan-2023-06-01T05:00:37Z",
]

# jun 3
# DBS = ['suns-cs-ucla-edu-2023-06-04T05:00:03Z', 'wundngw-2023-06-04T05:00:20Z',
#                  'hobo-2023-06-04T05:00:03Z', 'titan-2023-06-04T05:00:37Z']

# jun 1
# DBS = ['suns-cs-ucla-edu-2023-06-06T05:00:04Z', 'wundngw-2023-06-06T05:00:13Z',
#  'hobo-2023-06-06T05:00:03Z', 'titan-2023-06-06T05:00:37Z']

# # jun 9
# DBS = ['suns-cs-ucla-edu-2023-06-09T05:00:02Z', 'wundngw-2023-06-09T05:00:11Z',
#                  'hobo-2023-06-09T05:00:04Z', 'titan-2023-06-09T05:00:40Z']


class GridPacketsHistogramThroughput:
    def __init__(self, db, name, collections):
        self.db = db
        self.name = name
        self.collections = collections
        self.output = False

    async def plot(self, duration, ax1, ax2):
        LOGGER.info("Getting the packets...")
        i_ts = []
        d_ts = []
        r_ts = []
        i_sizes = []
        d_sizes = []
        r_sizes = []
        pipeline = [{"$project": {"_id": 0, "ts": 1, "size2": 1}}, {"$sort": {"ts": 1}}]
        for collection in self.collections.values():
            r = self.db[collection].aggregate(pipeline)
            async for doc in r:
                if collection == self.collections["INTEREST"]:
                    i_ts.append(doc["ts"])
                    i_sizes.append(doc["size2"])
                elif collection == self.collections["DATA"]:
                    d_ts.append(doc["ts"])
                    d_sizes.append(doc["size2"])
                else:
                    r_ts.append(doc["ts"])
                    r_sizes.append(doc["size2"])

        LOGGER.info("Preparing the data...")
        # Calculate number of packets / bytes in each duration
        start_time = datetime.utcfromtimestamp(min(i_ts[0], d_ts[0]) / 1e9)
        end_time = datetime.utcfromtimestamp(max(i_ts[-1], d_ts[-1]) / 1e9)
        d = int((end_time - start_time).total_seconds())
        num_durations = min(d // (duration * 60) + 1, 3 * 60 // duration)
        interest_num_packets = [0] * num_durations
        interest_ts = [0] * num_durations
        data_num_packets = [0] * num_durations
        data_ts = [0] * num_durations
        interest_throughput = [0] * num_durations
        data_throughput = [0] * num_durations
        r_throughput = [0] * num_durations

        def calculate_duration(packet_t):
            packet_duration = int(
                (datetime.utcfromtimestamp(packet_t / 1e9) - start_time).total_seconds()
                // (duration * 60)
            )
            return min(packet_duration, num_durations - 1)

        packet_data = [
            (i_ts, i_sizes, interest_num_packets, interest_ts, interest_throughput),
            (d_ts, d_sizes, data_num_packets, data_ts, data_throughput),
            (r_ts, r_sizes, None, None, r_throughput),
        ]
        for packets, sizes, num_packets, ts, throughput in packet_data:
            for packet_t, size in zip(packets, sizes):
                packet_duration = calculate_duration(packet_t)
                throughput[packet_duration] += size
                if num_packets is not None and ts is not None:
                    num_packets[packet_duration] += 1
                    ts[packet_duration] = datetime.utcfromtimestamp(packet_t / 1e9)
        throughput = [
            t * 8 / (duration * 60) / 1e6
            for t in (
                interest_throughput[i] + data_throughput[i] + r_throughput[i]
                for i in range(num_durations)
            )
        ]

        LOGGER.info("Plotting...")
        # First plot
        ax1.plot(
            np.arange(num_durations),
            [i / 1000 for i in interest_num_packets],
            color="#139061",
            label="Interests",
        )
        ax1.plot(
            np.arange(num_durations),
            [i / 1000 for i in data_num_packets],
            color="#AC9820",
            label="Data",
        )
        xformatter = ticker.FuncFormatter(
            lambda x, pos: (start_time + timedelta(minutes=x * duration)).strftime("%H:%M")
        )
        ax1.xaxis.set_major_formatter(xformatter)
        ax1.yaxis.set_major_formatter(ticker.ScalarFormatter())

        # Second plot
        ax2.plot(np.arange(num_durations), throughput, color="r", linestyle="-")
        ax2.xaxis.set_major_formatter(xformatter)
        label = None
        if "suns" in self.name:
            label = "UCLA"
        elif "wundngw" in self.name:
            label = "WU"
        elif "hobo" in self.name:
            label = "ARIZONA"
        elif "titan" in self.name:
            label = "MEMPHIS"
        ax2.set_xlabel(label, labelpad=10)

        ax1.spines["right"].set_visible(False)
        ax1.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)
        ax2.spines["top"].set_visible(False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot grid histogram throughput",
        prog="python -m tools.plots.grid_throughput",
    )
    parser.add_argument(
        "--duration",
        default=60,
        type=int,
        help="Duration in minutes to group packets (default: 60)",
    )
    parser.add_argument("-o", "--output", metavar="FILE", type=str, help="Save to file.")
    args = parser.parse_args()

    sns.set_context("paper", font_scale=1.5)
    fig, axs = plt.subplots(2, 4, figsize=(18, 6), sharex=True, sharey="row")
    tasks = []
    for ax in axs.flat:
        ax.tick_params(axis="both", which="major")
        ax.tick_params(axis="both", which="minor")
        for tick in ax.yaxis.get_major_ticks():
            tick.label1.set_visible(True)

    async def main():
        for i, db in enumerate(DBS):
            plot = GridPacketsHistogramThroughput(
                DB_CLIENT[db],
                db,
                {
                    "INTEREST": MONGO_COLLECTION_INTEREST,
                    "DATA": MONGO_COLLECTION_DATA,
                    "NACK": MONGO_COLLECTION_NACK,
                    "FRAGMENT": MONGO_COLLECTION_FRAGMENT,
                },
            )
            tasks.append(asyncio.create_task(plot.plot(args.duration, axs[0, i], axs[1, i])))
        await asyncio.gather(*tasks)

        # Create a common legend for all subplots
        handles, labels = axs[0, 0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="upper right")
        axs[0, 0].set_ylabel("Packets/min [x10^3]")
        axs[1, 0].set_ylabel("Mbps")
        for ax in axs.flat:
            ax.set_ylim(bottom=0)
        fig.supxlabel("Timestamp [UTC]")
        plt.tight_layout()

        if args.output:
            filename = PurePath(args.output).with_suffix(".pdf")
            plt.savefig(filename, bbox_inches="tight", dpi=300)
            LOGGER.info(f"Combined grid histogram throughput saved to {filename}")
        else:
            plt.show()

    asyncio.run(main())
