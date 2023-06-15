import os
import asyncio
import argparse
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator
from matplotlib.lines import Line2D
from collections import Counter
from settings import DB, LOGGER, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    DATA_DIR, MONGO_DB_NAME


class PopularPrefixes:
    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.save_fig = False

    async def plot(self):
        LOGGER.info('Getting the packets...')
        prefix_counters_interests = {}
        prefix_counters_data = {}

        for collection in self.collections.values():
            async for document in self.db[collection].find({}, {'_id': 0, 'ndn_genericnamecomponent': 1}):
                name_components = document['ndn_genericnamecomponent']

                for i in range(1, min(len(name_components), 5) + 1):  # Limit to first 5 levels
                    prefix = '/' + '/'.join(name_components[:i])
                    level = i

                    if collection == self.collections['INTEREST']:
                        if level not in prefix_counters_interests:
                            prefix_counters_interests[level] = Counter()
                        prefix_counters_interests[level][prefix] += 1
                    elif collection == self.collections['DATA']:
                        if level not in prefix_counters_data:
                            prefix_counters_data[level] = Counter()
                        prefix_counters_data[level][prefix] += 1

        # Get top 5 prefixes by count for each level for interests
        LOGGER.info('Getting the top prefixes...')
        top_prefixes_interests_per_level = {
            level: counter.most_common(5) for level, counter in prefix_counters_interests.items()
        }
        top_prefixes_data_per_level = {
            level: counter.most_common(5) for level, counter in prefix_counters_data.items()
        }

        LOGGER.info('Plotting...')
        fig, ax = plt.subplots(1, 2, figsize=(12, 7))
        fig.suptitle('Popularity of prefixes', fontsize=16)
        fig.subplots_adjust(top=0.5)

        ax[0].set_xlabel('Interests', fontsize=14)
        ax[1].set_xlabel('Data', fontsize=14)

        ax[0].xaxis.set_label_coords(0.5, -0.05)
        ax[1].xaxis.set_label_coords(0.5, -0.05)

        ax[0].set_ylabel('Count')
        ax[1].set_ylabel('Count')
        ax[0].set_yscale('log')
        ax[1].set_yscale('log')

        # Set the y-axis range and ticks for both plots
        min_count = min(
            [min(counter.values())
             for counter in list(prefix_counters_interests.values())]
            + [min(counter.values())
               for counter in list(prefix_counters_data.values())]
        )
        max_count = max(
            [max(counter.values())
             for counter in list(prefix_counters_interests.values())]
            + [max(counter.values())
               for counter in list(prefix_counters_data.values())]
        )

        ax[0].set_ylim(min_count, max_count)
        ax[1].set_ylim(min_count, max_count)
        # Set the y-axis to have more frequent ticks
        ax[0].yaxis.set_major_locator(LogLocator(numticks=10))
        ax[1].yaxis.set_major_locator(LogLocator(numticks=10))

        bar_width = 0.15
        colors = ['#66b3ff', '#99ff99', '#ff9999', '#ffcc99', '#c2c2f0']

        # Plot top 5 prefixes with counts only up to the 5th level
        for level in range(1, 6):
            interests_prefixes = top_prefixes_interests_per_level.get(
                level, [])
            data_prefixes = top_prefixes_data_per_level.get(level, [])
            offset = (level - 1) * 5
            color = colors[level - 1]

            for i, (prefix, count) in enumerate(interests_prefixes):
                bar = ax[0].bar(i + offset, count, width=bar_width,
                                color=color, label=f'Level {level}' if i == 0 else None)
                ax[0].text(i + offset, count + 0.2 * count, prefix, ha='center', va='bottom',
                           rotation='vertical', fontsize=8, fontdict={'style': 'italic'})

            for i, (prefix, count) in enumerate(data_prefixes):
                bar = ax[1].bar(i + offset, count, width=bar_width,
                                color=color, label=f'Level {level}' if i == 0 else None)
                ax[1].text(i + offset, count + 0.2 * count, prefix, ha='center', va='bottom',
                           rotation='vertical', fontsize=8, fontdict={'style': 'italic'})

        # Create custom legend using Line2D
        custom_lines = [Line2D([0], [0], color=colors[i], lw=4)
                        for i in range(5)]
        legend_labels = [f'Level {i+1}' for i in range(5)]

        # Place the legend outside the plots in the upper left
        fig.legend(custom_lines, legend_labels, loc='upper right')

        # Remove x-axis labels
        ax[0].set_xticklabels([])
        ax[1].set_xticklabels([])

        if self.save_fig:
            fig.savefig(os.path.join(
                DATA_DIR, f'{MONGO_DB_NAME}-popular_prefixes.pdf'), bbox_inches='tight')
            LOGGER.info(
                f'Popular prefixes saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-popular_prefixes.pdf")}')

        plt.show()
        plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot NDN packet statistics.', prog='python -m tools.plots.popular_prefixes')

    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = PopularPrefixes(
        DB, {'INTEREST': MONGO_COLLECTION_INTEREST, 'DATA': MONGO_COLLECTION_DATA})

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
