import argparse
import asyncio
from pathlib import PurePath

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib import ticker

from settings import *


class HopLimit:
    DEFAULT_HOPLIMIT = 255

    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.output = False

    async def plot(self):
        LOGGER.info("Getting packets....")
        hoplimits = []
        for _, collection in self.collections.items():
            async for document in self.db[collection].find({}, {"hopLimit": 1, "_id": 0}):
                if document.get("hopLimit"):
                    hoplimits.append(document.get("hopLimit"))

        counts = {}
        for hoplimit in hoplimits:
            counts[hoplimit] = counts.get(hoplimit, 0) + 1

        LOGGER.info("Plotting...")
        sns.set_context("paper", font_scale=3)
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.bar(counts.keys(), counts.values())
        ax.set_xlabel("Hop Limit")
        ax.set_ylabel("Count")
        ax.set_xlim(-5, 260)  # Margins of 5
        ax.set_ylim(bottom=0)
        ax.set_yscale("asinh")

        # Custom: This was added to add one more tick to the y-axis in the power of 10 and should
        # not be present for general plots
        max_count = max(counts.values())
        next_power_of_10 = 10 ** (int(np.log10(max_count)) + 1)
        ax.set_ylim(top=next_power_of_10)
        # Custom: End

        ax.xaxis.set_major_locator(ticker.MultipleLocator(25))
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(12.5))
        ax.tick_params(axis="both", which="major")
        ax.tick_params(axis="both", which="minor")
        ax.grid(axis="y")
        fig.tight_layout()

        if self.output:
            filename = PurePath(self.output).with_suffix(".pdf")
            fig.savefig(filename, bbox_inches="tight", dpi=300)
            LOGGER.info(f"Hop limit saved to {filename}")
        else:
            plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot hop limit CDF", prog="python -m tools.plots.hoplimit"
    )
    parser.add_argument("-o", "--output", metavar="FILE", type=str, help="Save to file.")
    args = parser.parse_args()

    plot = HopLimit(DB, {"INTEREST": MONGO_COLLECTION_INTEREST})

    plot.output = args.output
    asyncio.run(plot.plot())
