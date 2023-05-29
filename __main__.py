from aiohttp import web
from api import routes_components, routes_lp, routes_packets, routes_plots
import asyncio
import aiohttp_cors
import sys
from settings import SITE_HOST, SITE_PORT, DB_CLIENT, DB, LOGGER


async def start_server():
    app = web.Application()
    app.add_routes(routes_components)
    app.add_routes(routes_lp)
    app.add_routes(routes_packets)
    app.add_routes(routes_plots)

    cors = aiohttp_cors.setup(app, defaults={
        '*': aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers='*',
            allow_headers='*',
        )
    })

    for route in list(app.router.routes()):
        cors.add(route)

    app['db'] = DB

    async def cleanup():
        DB_CLIENT.close()
    app.on_cleanup.append(cleanup)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, SITE_HOST, SITE_PORT)
    await site.start()

    LOGGER.debug(
        f'Server started at http://{SITE_HOST}:{SITE_PORT}')


if __name__ == '__main__':
    if sys.version_info < (3, 7):
        loop = asyncio.get_event_loop()
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(start_server())
    loop.run_forever()
