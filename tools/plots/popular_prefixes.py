import argparse
import asyncio
from collections import Counter
from pathlib import PurePath

import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from ndn.encoding import Name

from settings import *

# For embedded fonts
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42


class PopularPrefixes:
    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.output = False

    async def plot(self):
        LOGGER.info("Getting the packets...")
        prefix_counters_interests = {}
        prefix_counters_data = {}

        for collection in self.collections.values():
            async for document in self.db[collection].find({}, {"_id": 0, "name": 1}):
                name_components = document["name"].split("/")[1:]

                for i in range(1, min(len(name_components), 5) + 1):  # Limit to first 5 levels
                    prefix = "/" + "/".join(name_components[:i])
                    level = i

                    if collection == self.collections["INTEREST"]:
                        if level not in prefix_counters_interests:
                            prefix_counters_interests[level] = Counter()
                        prefix_counters_interests[level][prefix] += 1
                    elif collection == self.collections["DATA"]:
                        if level not in prefix_counters_data:
                            prefix_counters_data[level] = Counter()
                        prefix_counters_data[level][prefix] += 1

        # Get top 3 prefixes by count for each level for interests
        LOGGER.info("Getting the top prefixes...")
        top_prefixes_interests_per_level = {
            level: counter.most_common(3) for level, counter in prefix_counters_interests.items()
        }
        top_prefixes_data_per_level = {
            level: counter.most_common(3) for level, counter in prefix_counters_data.items()
        }

        LOGGER.info("Plotting...")
        sns.set_context("paper", font_scale=2.5)
        fig, ax = plt.subplots(2, 1, figsize=(16, 14))
        ax[0].set_ylabel("Interests")
        ax[1].set_ylabel("Data")
        ax[1].set_xlabel("Count")
        ax[0].set_xscale("log")
        ax[1].set_xscale("log")
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

        y_ticks_interests = []
        y_ticks_labels_interests = []
        y_ticks_data = []
        y_ticks_labels_data = []

        # Plot top 5 prefixes with counts only up to the 5th level
        for level in range(1, 6):
            interests_prefixes = top_prefixes_interests_per_level.get(level, [])
            data_prefixes = top_prefixes_data_per_level.get(level, [])
            color = colors[level - 1]
            bar_start = (5 - level) * 10

            for i, (prefix, count) in enumerate(reversed(interests_prefixes)):
                y_pos = i * 3 + bar_start
                ax[0].barh(
                    y_pos,
                    count,
                    1.5,
                    alpha=0.4,
                    edgecolor="black",
                    color=color,
                )

                prefix = Name.to_str(Name.from_str(prefix))
                y_ticks_interests.append(y_pos)
                y_ticks_labels_interests.append(prefix)

            for i, (prefix, count) in enumerate(reversed(data_prefixes)):
                y_pos = i * 3 + bar_start
                ax[1].barh(
                    y_pos,
                    count,
                    1.5,
                    alpha=0.4,
                    edgecolor="black",
                    color=color,
                )

                prefix = Name.to_str(Name.from_str(prefix))
                y_ticks_data.append(y_pos)
                y_ticks_labels_data.append(prefix)

        x_min = min(ax[0].get_xlim()[0], ax[1].get_xlim()[0])
        x_max = max(ax[0].get_xlim()[1], ax[1].get_xlim()[1])
        ax[0].set_xlim(x_min, x_max)
        ax[1].set_xlim(x_min, x_max)

        ax[0].set_yticks(y_ticks_interests)
        ax[0].set_yticklabels(y_ticks_labels_interests)
        ax[1].set_yticks(y_ticks_data)
        ax[1].set_yticklabels(y_ticks_labels_data)

        ax[0].yaxis.set_label_position("right")
        ax[1].yaxis.set_label_position("right")
        ax[0].yaxis.set_ticks_position("none")
        ax[1].yaxis.set_ticks_position("none")

        ax[0].grid(axis="x", color="grey", linestyle="-.", linewidth=0.5, alpha=0.7)
        ax[1].grid(axis="x", color="grey", linestyle="-.", linewidth=0.5, alpha=0.7)

        # Create custom legend entries
        lines = [plt.Line2D([0], [0], color=c, linewidth=3, linestyle="-") for c in colors]
        labels = ["L1", "L2", "L3", "L4", "L5"]
        fig.legend(lines, labels, loc="upper left", bbox_to_anchor=(0, 1))

        fig.tight_layout()

        if self.output:
            filename = PurePath(self.output).with_suffix(".pdf")
            fig.savefig(filename, bbox_inches="tight", dpi=300)
            LOGGER.info(f"Popular prefixes saved to {filename}")
        else:
            plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot NDN packet statistics.",
        prog="python -m tools.plots.popular_prefixes",
    )
    parser.add_argument("-o", "--output", metavar="FILE", type=str, help="Save to file.")
    args = parser.parse_args()

    plot = PopularPrefixes(
        DB, {"INTEREST": MONGO_COLLECTION_INTEREST, "DATA": MONGO_COLLECTION_DATA}
    )

    plot.output = args.output
    asyncio.run(plot.plot())
