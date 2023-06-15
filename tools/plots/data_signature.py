import os
import asyncio
import argparse
import matplotlib.pyplot as plt
from ndn.encoding import SignatureType
from settings import DB, LOGGER, MONGO_COLLECTION_DATA, MONGO_DB_NAME, DATA_DIR


class DataSignature:
    def __init__(self, db):
        self.db = db
        self.save_fig = False

    async def plot(self):
        LOGGER.info('Getting packets....')
        sig_m = {
            SignatureType.NOT_SIGNED: "NOT_SIGNED",
            SignatureType.DIGEST_SHA256: "DIGEST_SHA256",
            SignatureType.SHA256_WITH_RSA: "SHA256_WITH_RSA",
            SignatureType.SHA256_WITH_ECDSA: "SHA256_WITH_ECDSA",
            SignatureType.HMAC_WITH_SHA256: "HMAC_WITH_SHA256",
            SignatureType.ED25519: "ED25519",
            SignatureType.NULL: "NULL"
        }

        counts = {}
        async for doc in DB[MONGO_COLLECTION_DATA].aggregate([{'$project': {'_id': 0, 'ndn_signaturetype': 1}}]):
            sig_type = doc['ndn_signaturetype']
            if sig_type is not None:
                sig_type = int(sig_type)
            counts[sig_m[sig_type]] = counts.get(sig_m[sig_type], 0) + 1

        LOGGER.info('Plotting....')
        plt.figure(figsize=(12, 7))
        plt.title('Signature Type Distribution')
        plt.xlabel('Signature Type')
        plt.ylabel('Count')
        plt.bar(counts.keys(), counts.values())
        plt.tight_layout()

        if self.save_fig:
            plt.savefig(os.path.join(DATA_DIR, f'{MONGO_DB_NAME}-data-signature.pdf'),
                        bbox_inches='tight')
            LOGGER.info(
                f'Data signature saved to {os.path.join(DATA_DIR, f"{MONGO_DB_NAME}-data-signature.pdf")}')

        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Plot data signature types', prog='python -m tools.plots.data_signature')

    parser.add_argument('--save-fig', default=False, action=argparse.BooleanOptionalAction,
                        help='Save figure to file (default: False).')
    args = parser.parse_args()

    plot = DataSignature(DB)

    plot.save_fig = args.save_fig
    asyncio.run(plot.plot())
