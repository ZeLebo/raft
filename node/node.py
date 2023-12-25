import asyncio
import sys
import traceback
from asyncio import sleep, StreamReader, StreamWriter, Event
from typing import Dict
from node.address import Address
from node.role import Role
from node.connection import Connection
from dataclasses import dataclass
from node.timer import Timer


# section REQUESTS
@dataclass
class RequestVote:
    term: int
    candidate_id: Address


@dataclass
class RequestVoteResponse:
    term: int
    vote_granted: bool


@dataclass
class AppendEntries:
    term: int
    leader_id: Address
    prev_log_index: int
    prev_log_term: int
    entries: list
    leader_commit: int


@dataclass()
class Heartbeat:
    term: int
    leader_id: Address


class Node:
    address: Address
    nodes: list[Address]
    role: Role
    leader: Address | None
    connections: Dict[Address, Connection]
    behavior: dict[Role, callable]
    term: int = 0
    timer: Timer
    event_to_listen: Event
    server: asyncio.AbstractServer
    voted_for: Address | None
    votes: int

    def __init__(self, host, port, nodes=None):
        self.voted_for = None
        self.votes = 0
        if nodes is None:
            nodes = []
        self.address = Address(host, port)
        self.nodes = nodes
        self.leader = None
        self.role = Role.FOLLOWER
        self.running = True
        self.connections = {}
        self.mutex = asyncio.Lock()
        self.event_to_listen = Event()
        self.behavior = {
            Role.LEADER: self.leader_behaviour,
            Role.FOLLOWER: self.follower_behaviour,
            Role.CANDIDATE: self.candidate_behaviour
        }
        self.message_callbacks = {
            RequestVote: self.on_request_vote,
            RequestVoteResponse: self.on_request_vote_response,
            AppendEntries: self.on_append_entries,
            Heartbeat: self.on_heartbeat
        }
        self.timer = Timer(1, self.on_timer)

    async def start(self):
        await asyncio.gather(
            self.make_connections(),
            self.receiver_loop(),
            self.run()
        )

    async def stop(self):
        self.running = False
        sys.exit(0)

    async def run(self):
        await self.timer.run()
        while self.running:
            print(f"Running as {self.role}")
            await self.behavior[self.role]()

    # section Connections
    async def make_connections(self):
        self.server = await asyncio.start_server(self.handle_connection, self.address.host, self.address.port)
        print(f"Starting server on {self.address}")
        self.event_to_listen.set()
        print(f"Making connections...")
        for node_adr in self.nodes:
            if node_adr in self.connections.keys():
                continue
            try:
                await self.mutex.acquire()
                self.connections[node_adr] = await self.open_connection(node_adr)
            except ConnectionRefusedError as e:
                print(f"Connection Refused {e}")
                await sleep(1)
            finally:
                self.mutex.release()
        print(f"Connections are established")

    async def open_connection(self, address):
        print(f"Connecting from {self.address} to {address}")
        conn = await asyncio.open_connection(address.host, address.port)
        return Connection(conn[0], conn[1])

    async def handle_connection(self, reader: StreamReader, writer: StreamWriter):
        peer = writer.get_extra_info('peername')
        ip, port = peer[0], peer[1]
        key = Address(ip, port)
        print(f"New connection from {key=}")
        self.connections[Address(ip, port)] = Connection(reader, writer)

    async def handle_disconnection(self, addr: Address):
        print(f"Disconnected from {addr}")
        try:
            await self.mutex.acquire()
            conn = self.connections[addr]
            conn.close()
        except KeyError as e:
            print(f"Connection with {addr} already closed from the other side {e}")
            return None
        finally:
            self.mutex.release()
        try:
            await self.mutex.acquire()
            self.connections.pop(addr)
        except KeyError:
            print(f"Cannot pop the connection with {addr} because it does not exist")
            return None
        finally:
            self.mutex.release()

    # section: Message handling
    async def send_message_to_all(self, message):
        for conn in list(self.connections.values()):
            try:
                await conn.send(message)
            except Exception as e:
                print(f"Exception during send message to all {e}")
                addr = conn.writer.get_extra_info('peername')
                await self.handle_disconnection(Address(addr[0], addr[1]))

    async def receiver_loop(self):
        await self.event_to_listen.wait()
        while self.running:
            await sleep(0.3)
            if len(self.connections.keys()) == 0:
                print("No connections...")
                await sleep(1)
                continue
            for conn in list(self.connections.values()):
                try:
                    message = await conn.receive()
                    await self.on_message_received(message)
                except EOFError as e:
                    print(f"EOFError {e}")
                except Exception as e:
                    print(f"Exception in receiver loop {e}")
                    addr = conn.writer.get_extra_info('peername')
                    await self.handle_disconnection(Address(addr[0], addr[1]))

    # section election
    async def on_timer(self):
        # if node was in follower state -> become candidate
        if self.role == Role.FOLLOWER:
            self.role = Role.CANDIDATE

    async def on_message_received(self, message):
        if type(message) in self.message_callbacks.keys():
            await self.message_callbacks[type(message)](message)
        else:
            print(f"Unknown message type {type(message)}")

    async def on_request_vote(self, message: RequestVote):
        print(f"Received request vote {message}")
        try:
            await self.timer.reset()
            if self.role == Role.FOLLOWER:
                await self.send_message(message.candidate_id, RequestVoteResponse(self.term, True))
                self.voted_for = message.candidate_id
            else:
                await self.send_message(message.candidate_id, RequestVoteResponse(self.term, False))
        except:
            import sys
            print("========================HUI===============================")
            traceback.print_exception(*sys.exc_info())

    async def on_request_vote_response(self, message: RequestVoteResponse):
        print(f"Received request vote response {message}")
        if message.vote_granted:
            self.votes += 1
            if self.votes > len(self.connections.keys()) // 2:
                self.role = Role.LEADER
                self.leader = self.address
                self.votes = 0
                self.voted_for = None
                await self.timer.reset()
        else:
            self.votes -= 1
            if self.votes <= 0:
                self.votes = 0
                self.voted_for = None
                await self.timer.reset()
                self.role = Role.FOLLOWER

    async def on_append_entries(self, message: AppendEntries):
        print(f"Received append entries {message}")
        if message.term < self.term:
            await self.send_message(message.leader_id, AppendEntries(self.term, self.address, 0, 0, [], 0))
        else:
            self.term = message.term
            self.leader = message.leader_id
            await self.timer.reset()
            self.role = Role.FOLLOWER
            await self.send_message(message.leader_id, AppendEntries(self.term, self.address, 0, 0, [], 0))

    async def on_heartbeat(self, message: Heartbeat):
        print(f"Received heartbeat {message}")
        self.leader = message.leader_id
        self.term = message.term
        self.role = Role.FOLLOWER
        await self.timer.reset()

    async def send_message(self, addr: Address, message):
        conn = self.connections[addr]
        await conn.send(message)

    async def leader_behaviour(self):
        print(f"Leader behaviour")
        await sleep(1)
        await self.send_message_to_all(Heartbeat(self.term, self.address))

    async def follower_behaviour(self):
        await self.timer.run()
        print(f"Follower behaviour")
        await sleep(1)

    async def candidate_behaviour(self):
        print(f"Candidate behaviour")
        self.votes = 1
        await self.send_message_to_all(RequestVote(self.term, self.address))
        await sleep(1)
