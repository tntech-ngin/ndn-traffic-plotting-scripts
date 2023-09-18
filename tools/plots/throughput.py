import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import PurePath

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib import ticker

from settings import *

# For embedded fonts
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42


class PacketsHistogramThroughput:
    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.output = False

    async def plot(self, duration):
        LOGGER.info("Getting the packets...")
        i_ts = []
        d_ts = []
        r_ts = []
        i_sizes = []
        d_sizes = []
        r_sizes = []
        pipeline = [
            {"$project": {"_id": 0, "ts": 1, "size2": 1}},
            {"$sort": {"ts": 1}},
        ]
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
        sns.set_context("paper", font_scale=1.5)
        fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(8, 8))
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
        ax1.set_ylim(bottom=0)
        ax1.set_ylabel("Packets/minute [x10^3]")
        ax1.legend(loc="upper right")

        # Second plot
        ax2.plot(np.arange(num_durations), throughput, color="r", linestyle="-")
        ax2.xaxis.set_major_formatter(xformatter)
        ax2.set_xlabel("Timestamp [UTC]")
        ax2.set_ylabel("Throughput [Mbps]")
        ax2.set_ylim(bottom=0)

        ax1.spines["right"].set_visible(False)
        ax1.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)
        ax2.spines["top"].set_visible(False)
        plt.tight_layout()

        if self.output:
            filename = PurePath(self.output).with_suffix(".pdf")
            fig.savefig(filename, bbox_inches="tight", dpi=300)
            LOGGER.info(f"Histogram saved to {filename}")
        else:
            plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot packets histogram",
        prog="python -m tools.plots.components_hexbin",
    )

    parser.add_argument(
        "--duration",
        default=60,
        type=int,
        help="Duration in minutes to group packets (default: 60)",
    )
    parser.add_argument("-o", "--output", metavar="FILE", type=str, help="Save to file.")
    args = parser.parse_args()

    plot = PacketsHistogramThroughput(
        DB,
        {
            "INTEREST": MONGO_COLLECTION_INTEREST,
            "DATA": MONGO_COLLECTION_DATA,
            "NACK": MONGO_COLLECTION_NACK,
            "FRAGMENT": MONGO_COLLECTION_FRAGMENT,
        },
    )

    plot.output = args.output
    asyncio.run(plot.plot(args.duration))
