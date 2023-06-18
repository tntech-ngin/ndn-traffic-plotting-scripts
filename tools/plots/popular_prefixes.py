import os
import asyncio
import argparse
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator
from collections import Counter
from ndn.encoding import Name
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
            async for document in self.db[collection].find({}, {'_id': 0, 'name': 1}):
                name_components = document['name'].split('/')[1:]

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

        # Get top 3 prefixes by count for each level for interests
        LOGGER.info('Getting the top prefixes...')
        top_prefixes_interests_per_level = {
            level: counter.most_common(3) for level, counter in prefix_counters_interests.items()
        }
        top_prefixes_data_per_level = {
            level: counter.most_common(3) for level, counter in prefix_counters_data.items()
        }

        LOGGER.info('Plotting...')
        fig, ax = plt.subplots(2, 1, figsize=(11, 6))

        ax[0].set_ylabel('Interests', fontsize=12)
        ax[1].set_ylabel('Data', fontsize=12)

        ax[0].yaxis.set_label_coords(-0.09, 0.5)
        ax[1].yaxis.set_label_coords(-0.09, 0.5)

        # ax[0].set_xlabel('Count')
        ax[1].set_xlabel('Count')
        ax[0].set_xscale('log')
        ax[1].set_xscale('log')

        # Set the y-axis to have more frequent ticks
        ax[0].yaxis.set_major_locator(LogLocator(numticks=10))
        ax[1].yaxis.set_major_locator(LogLocator(numticks=10))

        bar_width = 1.5
        colors = ['#66b3ff', '#99ff99', '#ff9999', '#ffcc99', '#c2c2f0']

        # Plot top 5 prefixes with counts only up to the 5th level
        for level in range(5, 0, -1):
            interests_prefixes = top_prefixes_interests_per_level.get(
                level, [])
            data_prefixes = top_prefixes_data_per_level.get(level, [])
            offset = (5 - level) * 40
            color = colors[level - 1]

            for i, (prefix, count) in enumerate(interests_prefixes):
                bar = ax[0].barh(i * 12 + offset, count, height=bar_width,
                                 color=color, label=f'Level {level}' if i == 0 else None)

                prefix = Name.to_str(Name.from_str(prefix))
                ax[0].text(count + 0.2 * count, i * 12 + offset, prefix, ha='left', va='center',
                           rotation=0, fontsize=8, fontdict={'style': 'italic'})

            for i, (prefix, count) in enumerate(data_prefixes):
                bar = ax[1].barh(i * 12 + offset, count, height=bar_width,
                                 color=color, label=f'Level {level}' if i == 0 else None)

                prefix = Name.to_str(Name.from_str(prefix))
                ax[1].text(count + 0.2 * count, i * 12 + offset, prefix, ha='left', va='center',
                           rotation=0, fontsize=8, fontdict={'style': 'italic'})

        ax[0].set_xlim(1e3, 1e7)
        ax[1].set_xlim(1e3, 1e7)

        ax[0].set_yticks([172, 132, 92, 52, 12])
        ax[1].set_yticks([172, 132, 92, 52, 12])

        ax[0].set_ylim(-10)
        ax[1].set_ylim(-10)

        ax[0].spines['right'].set_visible(False)
        ax[0].spines['top'].set_visible(False)
        ax[1].spines['right'].set_visible(False)
        ax[1].spines['top'].set_visible(False)

        ax[0].set_yticklabels(
            ['Level 1', 'Level 2', 'Level 3', 'Level 4', 'Level 5'], fontsize=9)
        ax[1].set_yticklabels(
            ['Level 1', 'Level 2', 'Level 3', 'Level 4', 'Level 5'], fontsize=9)

        ax[0].yaxis.set_ticks_position('none')
        ax[1].yaxis.set_ticks_position('none')

        fig.tight_layout()

        if self.save_fig:
            fig.savefig(os.path.join(
                DATA_DIR, f'{MONGO_DB_NAME}-popular_prefixes.pdf'), bbox_inches='tight')
            LOGGER.info(
                f'Popular prefixes saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-popular_prefixes.pdf")}')
        else:
            plt.show()


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
