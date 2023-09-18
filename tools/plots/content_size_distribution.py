import argparse
import asyncio
from pathlib import PurePath

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from settings import *

# For embedded fonts
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42


class NLSRContentSizeDistribution:
    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.output = False

    async def plot(self):
        search_term = "nlsr"
        content_sizes = []

        LOGGER.info("Getting the packets...")
        for collection in self.collections.values():
            async for packet in self.db[collection].find({}, {"_id": 0, "name": 1, "size3": 1}):
                if search_term in packet["name"]:
                    content_sizes.append(packet["size3"])

        # Custom: This was done to get the count divided by 10^4 for aesthetic reasons and
        # should not be present for general plots
        LOGGER.info("Preparing the data...")
        counts, bin_edges = np.histogram(content_sizes, bins=80)
        counts = counts / 10**4
        # End

        LOGGER.info("Plotting...")
        sns.set_context("paper", font_scale=3)
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.grid(axis="y")

        # Custom: This was done to get the count divided by 10^4 for aesthetic reasons and
        # should not be present for general plots
        for i in range(len(bin_edges) - 1):
            ax.hist(
                [bin_edges[i]],
                bins=[bin_edges[i], bin_edges[i + 1]],
                weights=[counts[i]],
                color="#4787BB",
                edgecolor="black",
            )
        # End

        # Uncomment for generic case
        # ax.hist(content_sizes, bins=80, color="#4787BB", edgecolor="black")
        major_ticks = ax.get_xticks()
        minor_ticks = (major_ticks[:-1] + major_ticks[1:]) / 2
        ax.set_xticks(minor_ticks, minor=True)
        ax.tick_params(axis="x", which="minor", labelsize=0)
        ax.set_xlabel("Data Packet Size (Bytes)")
        ax.set_ylabel(r"Count (x$10^4$)")
        # Uncomment for generic case
        # ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
        ax.tick_params(axis="both", which="major")
        ax.tick_params(axis="both", which="minor")
        plt.tight_layout()

        if self.output:
            filename = PurePath(self.output).with_suffix(".pdf")
            fig.savefig(filename, bbox_inches="tight", dpi=300)
            LOGGER.info(f"Content size distribution saved to {filename}")
        else:
            plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot content size distribution for data packets.",
        prog="python -m tools.plots.content_size_distribution",
    )
    parser.add_argument("-o", "--output", metavar="FILE", type=str, help="Save to file.")
    args = parser.parse_args()

    plot = NLSRContentSizeDistribution(DB, {"DATA": MONGO_COLLECTION_DATA})

    plot.output = args.output
    asyncio.run(plot.plot())
