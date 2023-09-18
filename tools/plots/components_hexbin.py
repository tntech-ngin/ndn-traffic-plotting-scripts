import argparse
import asyncio
from pathlib import PurePath

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib import colors
from ndn.encoding import Name

from settings import *

# For embedded fonts
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42


class ComponentsHexbin:
    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.output = False

    async def plot(self):
        LOGGER.info("Getting the packets...")
        i_d = []
        d_d = []
        for collection in self.collections.values():
            async for document in self.db[collection].find({}, {"name": 1, "_id": 0}):
                n = document["name"]
                num_c = len(n.split("/")) - 1
                try:
                    name_len = len(Name.to_bytes(n))
                except ValueError as e:
                    LOGGER.warning(f"Invalid name: {n}. Error: {e}")
                    continue

                if collection == self.collections["INTEREST"]:
                    i_d.append((num_c, name_len))
                elif collection == self.collections["DATA"]:
                    d_d.append((num_c, name_len))

        LOGGER.info("Plotting...")
        sns.set_context("paper", font_scale=2)
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.tick_params(axis="both", which="major")
        hb1 = ax.hexbin(
            *zip(*i_d),
            gridsize=25,
            cmap="Blues",
            alpha=0.9,
            mincnt=25,
            edgecolors="blue",
        )
        hb2 = ax.hexbin(
            *zip(*d_d),
            gridsize=25,
            cmap="Oranges",
            alpha=0.9,
            mincnt=25,
            edgecolors="orange",
        )

        max_count = max(hb1.get_array().max(), hb2.get_array().max())
        min_count = min(hb1.get_array().min(), hb2.get_array().min())
        norm = colors.Normalize(vmin=min_count, vmax=max_count)

        hb1 = ax.hexbin(
            *zip(*i_d),
            gridsize=25,
            cmap="Blues",
            norm=norm,
            alpha=0.9,
            mincnt=25,
            edgecolors="blue",
        )
        hb2 = ax.hexbin(
            *zip(*d_d),
            gridsize=25,
            cmap="Oranges",
            norm=norm,
            alpha=0.9,
            mincnt=25,
            edgecolors="orange",
        )

        cb1 = fig.colorbar(hb1)
        cb2 = fig.colorbar(hb2)
        cb1.set_label("Interest Frequency")
        cb2.set_label("Data Frequency")

        ax.set_xlabel("Number of Components")
        ax.set_ylabel("Name Length (Bytes)")

        ax.grid(axis="y")
        ax.tick_params(axis="both", which="major")

        # Custom: This code was added to define explicit x and y limits and should not be used
        ax.set_xlim(left=0, right=14)
        ax.set_ylim(bottom=0, top=800)
        ax.yaxis.set_ticks(np.arange(0, 801, 50))
        # Custom: End

        if self.output:
            filename = PurePath(self.output).with_suffix(".pdf")
            fig.savefig(filename, bbox_inches="tight", dpi=300)
            LOGGER.info(f"Hexbin saved to {filename}")
        else:
            plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot components distribution hexbin",
        prog="python -m tools.plots.components_hexbin",
    )
    parser.add_argument("-o", "--output", metavar="FILE", type=str, help="Save to file.")
    args = parser.parse_args()

    plot = ComponentsHexbin(
        DB, {"INTEREST": MONGO_COLLECTION_INTEREST, "DATA": MONGO_COLLECTION_DATA}
    )

    plot.output = args.output
    asyncio.run(plot.plot())
