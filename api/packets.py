import aiohttp
import bson
from ndn.encoding import SignatureType
from settings import DB, MONGO_COLLECTION_DATA, MONGO_COLLECTION_LP_PACKET_DATA

routes_packets = aiohttp.web.RouteTableDef()


@routes_packets.get('/packets-stats/')
async def average_depth(request):
    r = {}
    for c_name in await DB.list_collection_names():
        r[c_name] = await DB[str(c_name)].count_documents({})

    return aiohttp.web.json_response(status=aiohttp.web.HTTPOk.status_code,
                                     data=r)


@routes_packets.get('/packets/{packet_id}/')
async def per_packet_info(request):
    r = None
    try:
        for c_name in await DB.list_collection_names():
            r = await DB[str(c_name)].find_one({'_id': bson.ObjectId(request.match_info['packet_id'])}, {'_id': 0})
            if r is not None:
                break
    except bson.errors.InvalidId:
        return aiohttp.web.json_response(status=aiohttp.web.HTTPNotFound.status_code,
                                         data={'error': f'Packet `{request.match_info["packet_id"]}` not found'})
    else:
        if r is None:
            return aiohttp.web.json_response(status=aiohttp.web.HTTPNotFound.status_code,
                                             data={'error': f'Packet `{request.match_info["packet_id"]}` not found'})

    return aiohttp.web.json_response(status=aiohttp.web.HTTPOk.status_code, data=r)


@routes_packets.get('/packets/data/signature/')
async def data_signature(request):
    sig_m = {
        SignatureType.NOT_SIGNED: "NOT_SIGNED",
        SignatureType.DIGEST_SHA256: "DIGEST_SHA256",
        SignatureType.SHA256_WITH_RSA: "SHA256_WITH_RSA",
        SignatureType.SHA256_WITH_ECDSA: "SHA256_WITH_ECDSA",
        SignatureType.HMAC_WITH_SHA256: "HMAC_WITH_SHA256",
        SignatureType.ED25519: "ED25519",
        SignatureType.NULL: "NULL"
    }
    pipeline = [{'$project': {'_id': 0, '_source.layers.ndn': 1}}]
    collections = [MONGO_COLLECTION_DATA, MONGO_COLLECTION_LP_PACKET_DATA]

    counts = {}
    for collection in collections:
        async for doc in DB[collection].aggregate(pipeline):
            if collection == MONGO_COLLECTION_DATA:
                sig_type = doc['_source']['layers']['ndn']['ndn_signatureinfo']['ndn_signaturetype']
            elif collection == MONGO_COLLECTION_LP_PACKET_DATA:
                sig_type = doc['_source']['layers']['ndn'][1]['ndn_signatureinfo']['ndn_signaturetype']
            if sig_type is not None:
                sig_type = int(sig_type)
            counts[sig_m[sig_type]] = counts.get(sig_m[sig_type], 0) + 1

    return aiohttp.web.json_response(status=aiohttp.web.HTTPOk.status_code, data=counts)