from misc.arg_parse import parse
from node.node import Node
from asyncio import run
import uvicorn
from fastapi import FastAPI
from sys import exit

app = FastAPI()


async def start_server(host, port):
    config = uvicorn.Config(app, host=host, port=port)
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    host, port, nodes_address = parse()
    node = Node(host, port, nodes_address)

    @app.get("/add_entry")
    async def root():
        return {"message": "Hello World"}

    @app.get("/kill")
    async def kill():
        node.running = False
        return {"message": "Killed"}

    # from asyncio import gather
    # tasks = [node.start(), start_server(host, port)]
    # await gather(*tasks)
    await node.start()


if __name__ == '__main__':
    try:
        run(main())
    except RuntimeError as e:
        print("Handled RuntimeError", e)
    except KeyboardInterrupt:
        print("Exiting...")
        exit(0)
