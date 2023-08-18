import argparse
import asyncio
from pathlib import PurePath

import matplotlib.pyplot as plt
import seaborn as sns

from settings import *


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

        LOGGER.info("Plotting...")
        sns.set_context("paper", font_scale=2)
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.grid(axis="y")
        ax.hist(content_sizes, bins=80, color="#4787BB", edgecolor="black")
        ax.set_xlabel("Data Packet Size [Bytes]")
        ax.set_ylabel("Count")
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
