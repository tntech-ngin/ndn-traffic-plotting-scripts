import argparse
import asyncio
from pathlib import PurePath

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib import ticker

from settings import *


class LifetimeFreshnessCDF:
    DEFAULT_LIFETIME = 4000
    DEFAULT_FRESHNESS = 0

    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.output = False

    async def plot(self):
        LOGGER.info("Getting the packets...")
        interest_lifetime_values = []
        data_freshness_values = []
        for collection_name, collection in self.collections.items():
            async for document in self.db[collection].find(
                {}, {"lifetime": 1, "freshness": 1, "_id": 0}
            ):
                if collection_name == "INTEREST":
                    interest_lifetime_values.append(
                        document.get("lifetime", LifetimeFreshnessCDF.DEFAULT_LIFETIME)
                    )
                elif collection_name == "DATA":
                    if document.get("freshness"):
                        data_freshness_values.append(document.get("freshness"))

        interest_lifetime_values.sort()
        data_freshness_values.sort()
        interest_lifetime_cdf = np.arange(1, len(interest_lifetime_values) + 1) / len(
            interest_lifetime_values
        )
        data_freshness_cdf = np.arange(1, len(data_freshness_values) + 1) / len(
            data_freshness_values
        )

        LOGGER.info("Plotting...")
        sns.set_context("paper", font_scale=3)
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.plot(
            interest_lifetime_values,
            interest_lifetime_cdf,
            label="Interest lifetime",
            linewidth=3,
        )
        ax.plot(
            data_freshness_values,
            data_freshness_cdf,
            label="Freshness period",
            color="r",
            linewidth=3,
        )

        # Custom: This was added to show vertical lines at every power of 10 until 10^8 and
        # should not be present for general plots
        for i in range(1, 9):
            ax.axvline(10**i, color="k", linewidth=0.1, alpha=0.3)
            ax.grid(True, axis="y", linewidth=0.2, alpha=0.5)
        # Custom: End

        ax.set_xlim(1, 1e8)
        ax.set_ylim(0, 1)
        ax.set_xscale("log")
        ax.set_xlabel("Milliseconds")
        ax.set_ylabel("CDF")
        # Uncomment for generic case
        # ax.grid(True)
        ax.legend(loc="upper left", fontsize="small")
        ax.xaxis.set_minor_locator(ticker.LogLocator(base=10, subs=np.arange(1, 10.0), numticks=10))
        # ax.set_yticks(np.linspace(0, 1, num=11))
        ax.yaxis.set_minor_locator(plt.MultipleLocator(0.1))
        ax.tick_params(axis="both", which="major")
        ax.tick_params(axis="both", which="minor")
        fig.tight_layout()

        if self.output:
            filename = PurePath(self.output).with_suffix(".pdf")
            fig.savefig(filename, bbox_inches="tight", dpi=300)
            LOGGER.info(f"Lifetimefreshness cdf saved to {filename}")
        else:
            plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot interest lifetime cdf",
        prog="python -m tools.plots.lifetime_freshness",
    )
    parser.add_argument("-o", "--output", metavar="FILE", type=str, help="Save to file.")
    args = parser.parse_args()

    plot = LifetimeFreshnessCDF(
        DB, {"INTEREST": MONGO_COLLECTION_INTEREST, "DATA": MONGO_COLLECTION_DATA}
    )

    plot.output = args.output
    asyncio.run(plot.plot())
