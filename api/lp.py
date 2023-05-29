import aiohttp
from settings import DB, MONGO_COLLECTION_LP_PACKET_NACK, MONGO_COLLECTION_INTEREST, \
    MONGO_COLLECTION_DATA


routes_lp = aiohttp.web.RouteTableDef()


@routes_lp.get('/nacks/')
async def nacks(request):
    nacks = DB[MONGO_COLLECTION_LP_PACKET_NACK].aggregate([
        {
            '$group': {
                '_id': '$_source.layers.ndn.ndn_nack_tree.ndn_nackreason',
                'count': {'$sum': 1}
            }
        },
        {
            '$project': {
                'type': '$_id',
                'count': 1,
                '_id': 0
            }
        }
    ])

    nacks = [nack async for nack in nacks]
    if len(nacks) == 0:
        return aiohttp.web.json_response(status=aiohttp.web.HTTPNotFound.status_code,
                                         data={'error': 'No NACKs found'})
    
    counts = {}
    for nack in nacks:
        counts[nack['type'][0]] = nack['count']

    return aiohttp.web.json_response(status=aiohttp.web.HTTPOk.status_code, data=counts)


# WIP
@routes_lp.get('/timeouts/')
async def timeouts(request):
    page_size = 1
    page_num = 2

    timeouts = DB[MONGO_COLLECTION_INTEREST].aggregate([
        {
            '$lookup': {
                'from': MONGO_COLLECTION_DATA,
                'localField': '_source.layers.ndn.ndn_nonce',
                'foreignField': '_source.layers.ndn.ndn_nonce',
                'as': 'data_packet'
            }
        },
        {
            '$match': {
                'data_packet': {'$not': {'$size': 0}}
            }
        },
        {
            '$project': {
                '_id': 0,
            }
        },
        {
            "$skip": page_size * (page_num - 1)
        },
        {
            "$limit": page_size
        }
    ])

    timeouts = [timeout async for timeout in timeouts]
    if len(timeouts) == 0:
        return aiohttp.web.json_response(status=aiohttp.web.HTTPNotFound.status_code,
                                         data={'error': 'No timeouts found'})

    return aiohttp.web.json_response(status=aiohttp.web.HTTPOk.status_code, data=timeouts)
