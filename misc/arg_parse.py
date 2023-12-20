import argparse

from misc.network_utils import get_local_ip
from node.address import Address


def parse():
    parser = argparse.ArgumentParser(description='Self implemented RAFT')
    parser.add_argument('-host', type=str, default='127.0.0.1', help="ip you wanna listen at")
    parser.add_argument('-port', type=int, default=9090, help="port you wanna listen at")
    parser.add_argument('-other', nargs='+', default='', help="ip:port of nodes")

    args = parser.parse_args()
    # if host is "localhost" then we need to change it to "127.0.0.1"
    if args.host == 'localhost':
        args.host = '127.0.0.1'
    if len(args.host) < 7:
        args.host = get_local_ip()
    host = args.host
    port = args.port

    nodes_address: list[Address] = []
    for other_node in args.other:
        other_node = other_node.split(':')
        node_host, node_port = other_node[0], int(other_node[1])
        if node_host == 'localhost':
            node_host = '127.0.0.1'
        nodes_address.append(Address(node_host, node_port))

    print(f"Host: {host}, Port: {port}, Nodes: {nodes_address}")

    return host, port, nodes_address
