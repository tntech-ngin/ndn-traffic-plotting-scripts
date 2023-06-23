import asyncio
import argparse
import os
import seaborn as sns
import matplotlib.pyplot as plt
from settings import DB, LOGGER, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_DATA, \
    DATA_DIR, MONGO_DB_NAME


class ParametersUsage:
    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.save_fig = False

    async def plot(self):
        LOGGER.info('Getting the packets...')
        mbf = 0
        cbp = 0
        freshness = 0

        pipeline = {
            'mbf': 1,
            'cbp': 1,
            'freshness': 1,
            '_id': 0
        }
        for collection in self.collections.values():
            async for document in self.db[collection].find({}, pipeline):
                if collection == MONGO_COLLECTION_INTEREST:
                    mbf = document.get('mbf', None)
                    cbp = document.get('cbp', None)
                    if mbf == True:
                        mbf += 1
                    if cbp == True:
                        cbp += 1
                elif collection == MONGO_COLLECTION_DATA:
                    f = document.get('freshness', None)
                    if f and f > 0:
                        f += 1

        print(f'mbf: {mbf}, cbp: {cbp}, freshness: {freshness}')

        # parameters_percentage = {
        #     'mbf': round(parameters_count['mustbefresh'] / total * 100, 2),
        #     'cbp': round(parameters_count['canbeprefix'] / total * 100, 2),
        #     # 'interestlifetime': round(parameters_count['interestlifetime'] / total * 100, 2),
        #     # 'interestsignatureinfo': round(parameters_count['interestsignatureinfo'] / total * 100, 2),
        #     # 'hoplimit': round(parameters_count['hoplimit'] / total * 100, 2)
        # }

        # LOGGER.info('Plotting...')
        # fig, ax = plt.subplots(figsize=(12, 7))
        # sns.barplot(x=list(parameters_percentage.keys()),
        #             y=list(parameters_percentage.values()), ax=ax, palette='gray')
        # ax.set_title('Parameters usage', pad=30)
        # ax.set_xlabel('Parameters', labelpad=10)
        # ax.set_ylabel('Percentage (%)', labelpad=10)
        # ax.set_ylim(0, 100)
        # ax.bar_label(ax.containers[0], fmt='%.2f', label_type='edge')

        # ax.spines['top'].set_visible(False)
        # ax.spines['right'].set_visible(False)

        # plt.xticks(range(len(parameters_percentage)),
        #            list(parameters_percentage.keys()))

        # if self.save_fig:
        #     fig.savefig(os.path.join(
        #         DATA_DIR, f'{MONGO_DB_NAME}-parameters_usage.pdf'), bbox_inches='tight')
        #     LOGGER.info(
        #         f'Parameters usage saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-parameters_usage.pdf")}')

        # plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot parameters usage', prog='python -m tools.plots.parameters_usage')

    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = ParametersUsage(DB, {'INTEREST': MONGO_COLLECTION_INTEREST, 'DATA': MONGO_COLLECTION_DATA})

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
