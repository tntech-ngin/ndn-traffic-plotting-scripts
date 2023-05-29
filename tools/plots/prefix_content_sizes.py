import asyncio
import argparse
import binascii
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from settings import DB, LOGGER, MONGO_COLLECTION_DATA, \
    MONGO_COLLECTION_LP_PACKET_DATA, DATA_DIR, MONGO_DB_NAME


class PrefixContentSizes:
    def __init__(self, db, collections):
        self.db = db
        self.collections = collections
        self.save_fig = False

    async def plot(self):
        if os.path.exists(os.path.join(DATA_DIR, f'{MONGO_DB_NAME}-prefix-content-sizes.csv')):
            df = pd.read_csv(os.path.join(
                DATA_DIR, f'{MONGO_DB_NAME}-prefix-content-sizes.csv'))
            LOGGER.info('Plotting...')
            fig, axs = plt.subplots(1, 2, figsize=(12, 7))
            axs[0].bar(df.columns, df.mean(), color=['#1f77b4', '#ff7f0e'], alpha=0.7)
            axs[0].set_xlabel('Term')
            axs[0].set_ylabel('Average content size (bytes)')
            axs[0].set_title('Average content size per term')

            # Separate plots for distributions
            if df['nlsr'].nunique() > 1:  # Check if 'nlsr' has more than one unique value
                sns.histplot(df['nlsr'].dropna(), kde=True, ax=axs[1])  # Plot histogram with kernel density estimate for 'nlsr'
                axs[1].set_title('Content size distribution for nlsr')
                axs[1].set_xlabel('Content Size')

            if self.save_fig:
                fig.savefig(os.path.join(
                    DATA_DIR, f'{MONGO_DB_NAME}-prefix_content_sizes.pdf'), bbox_inches='tight')
                LOGGER.info(
                    f'Prefix content sizes saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-prefix_content_sizes.pdf")}')

            plt.tight_layout()
            plt.show()
            
            return

        search_terms = ['fileserver', 'nlsr']
        content_sizes = {term: [] for term in search_terms}

        pipeline = {
            '_source.layers.ndn.ndn_name_tree.ndn_genericnamecomponent': 1,
            '_source.layers.ndn._ws_lua_text.ndn_content': 1,
            '_id': 0}

        LOGGER.info('Getting the packets...')
        for collection in self.collections.values():
            async for packet in self.db[collection].find({}, pipeline):
                name_components = packet['_source']['layers']['ndn'][1]['ndn_name_tree']['ndn_genericnamecomponent'] if collection == self.collections[
                    'LP_PACKET_DATA'] else packet['_source']['layers']['ndn']['ndn_name_tree']['ndn_genericnamecomponent']

                for term in content_sizes.keys():
                    if any(term in comp for comp in name_components):
                        content = packet['_source']['layers']['ndn'][1]['_ws_lua_text']['ndn_content'] if collection == self.collections[
                            'LP_PACKET_DATA'] else packet['_source']['layers']['ndn']['_ws_lua_text']['ndn_content']

                        content_bytes = binascii.unhexlify(
                            content.replace(':', ''))
                        content_size = len(content_bytes)

                        content_sizes[term].append(content_size)

        LOGGER.info('Preparing data...')
        df = pd.DataFrame.from_dict(content_sizes, orient='index').transpose()

        # save df to file for later use
        df.to_csv(os.path.join(
            DATA_DIR, f'{MONGO_DB_NAME}-prefix-content-sizes.csv'), index=False)

        LOGGER.info('Plotting...')
        fig, axs = plt.subplots(1, 2, figsize=(12, 14))
        axs[0].bar(df.columns, df.mean(), color=['#1f77b4', '#ff7f0e'], alpha=0.7)
        axs[0].set_xlabel('Term')
        axs[0].set_ylabel('Average content size (bytes)')
        axs[0].set_title('Average content size per term')

        for column in df.columns:
            if df[column].nunique() > 1:  # Only plot distributions for columns with more than one unique value
                sns.histplot(df[column].dropna(), kde=True, ax=axs[1])  # Plot histogram with kernel density estimate
                axs[1].set_title(f'Content size distribution for {column}')

        if self.save_fig:
            fig.savefig(os.path.join(
                DATA_DIR, f'{MONGO_DB_NAME}-prefix_content_sizes.pdf'), bbox_inches='tight')
            LOGGER.info(
                f'Prefix content sizes saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-prefix_content_sizes.pdf")}')

        plt.tight_layout()
        plt.show()



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot prefixes to content sizes for data packets.', prog='python -m tools.plots.prefix_content_sizes')

    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = PrefixContentSizes(
        DB, {'DATA': MONGO_COLLECTION_DATA, 'LP_PACKET_DATA': MONGO_COLLECTION_LP_PACKET_DATA})

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
