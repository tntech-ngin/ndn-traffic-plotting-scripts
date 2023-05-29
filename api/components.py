import aiohttp
import bson
from settings import DB, MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_LP_PACKET_INTEREST

routes_components = aiohttp.web.RouteTableDef()


@routes_components.get('/components/')
async def average_depth(request):
    # pipeline = [{'$project': {'_id': 0, '_source.layers.ndn': 1}}]
    # collections = [MONGO_COLLECTION_INTEREST, MONGO_COLLECTION_LP_PACKET_INTEREST]
    interests = DB[MONGO_COLLECTION_INTEREST].aggregate([
        {
            '$project': {
                '_source.layers.ndn.ndn_name': 1,
                'totalComponents': {'$size': '$_source.layers.ndn.ndn_name_tree.ndn_genericnamecomponent'}
            }
        }
    ])

    total_components = 0
    total_documents = 0
    async for document in interests:
        total_components += document['totalComponents']
        total_documents += 1

    average_depth = total_components / total_documents

    return aiohttp.web.json_response(status=aiohttp.web.HTTPOk.status_code,
                                     data={'average_depth': average_depth, 'total_interests': total_documents})


@routes_components.get('/components/{packet_id}/')
async def c_per_packet_info(request):
    try:
        document = await DB[MONGO_COLLECTION_INTEREST].find_one(
            {'_id': bson.ObjectId(request.match_info['packet_id'])}, {'_id': 0, '_source.layers.ndn.ndn_name_tree': 1, '_source.layers.ndn.ndn_name': 1})
    except bson.errors.InvalidId:
        return aiohttp.web.json_response(status=aiohttp.web.HTTPNotFound.status_code,
                                         data={'error': f'Packet `{request.match_info["packet_id"]}` not found'})
    else:
        if document is None:
            return aiohttp.web.json_response(status=aiohttp.web.HTTPNotFound.status_code,
                                             data={'error': f'Packet `{request.match_info["packet_id"]}` not found'})

    return aiohttp.web.json_response(status=aiohttp.web.HTTPOk.status_code, data={
        'total_components': len(document['_source']['layers']['ndn']['ndn_name_tree']['ndn_genericnamecomponent']),
        'ndn_name': document['_source']['layers']['ndn']['ndn_name'],
        'components': document['_source']['layers']['ndn']['ndn_name_tree']['ndn_genericnamecomponent'],
        'name_component': document['_source']['layers']['ndn']['ndn_name_tree']['ndn_nameComponent'] if
        'ndn_nameComponent' in document['_source']['layers']['ndn']['ndn_name_tree'] else None
    })
