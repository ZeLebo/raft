from asyncio import StreamReader, StreamWriter, wait_for
from dataclasses import dataclass
# if using json it will try to serialize the object to the string
# pickle will serialize the object to bytes
import pickle
from pprint import pprint


@dataclass
class Connection:
    reader: StreamReader
    writer: StreamWriter

    def close(self):
        self.writer.close()

    async def send(self, message):
        serialized_message = pickle.dumps(message)
        size = len(serialized_message).to_bytes(8, byteorder='big')
        self.writer.write(size + serialized_message)
        await wait_for(self.writer.drain(), timeout=2)

    async def receive(self) -> str | dict:
        size = int.from_bytes(await self.reader.read(8), byteorder='big')
        message = await self.reader.read(size)
        message = pickle.loads(message)
        return message
