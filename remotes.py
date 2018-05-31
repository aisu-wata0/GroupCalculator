#!python

import socket


# Opens servers.txt to extract a remote_list
# each entry has a tuple (hostname, port) of the remote server
# Finds out the server_id of the server
# (host, port, udp) passed as optional arguments
# if udp, ignores port values in remotes and argument
# returns remote_list, server_id
# server_id is not useful to client
def create_remote_list(my_name="", my_port=-1, udp=False):
    # initialize variables
    remote_list = []
    index = 0
    server_id = -1
    if udp:
        my_port = -1

    file = open("servers.txt", "r")
    for line in file:
        # parse addr and port from line, example: line = "hostname 1111" => ["hostname", "1111"]
        remote = line.split(" ")
        addr = remote[0]
        port = -1
        if not udp:
            port = int(remote[1])
            remote = (addr, port)
        # append remote (address,port) tuple in remote_list
        remote_list.append(remote)
        print("Registered remote " + str(remote))
        # check if it's my address and port, to find out my id
        if socket.gethostbyname(addr) == my_name and port == my_port:
            server_id = index
            print("I am server #%d" % server_id)
        index += 1

    return remote_list, server_id
