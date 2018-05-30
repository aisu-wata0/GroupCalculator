#!python

import socket


# Opens servers.txt to extract a remote_list
# each entry has a tuple (hostname, port) of the remote server
# It also finds out the server_id of the server
# (host, port) passed as optional arguments
# returns remote_list, server_id
# server_id is not useful to client
def create_remote_list(my_name="", my_port=-1):
    # initialize variables
    remote_list = []
    index = 0
    server_id = -1

    file = open("servers.txt", "r")
    for line in file:
        # parse addr and port from line, example: line = "hostname 1111" => ["hostname", "1111"]
        addr, port = line.split(" ")
        port = int(port)
        # append remote (address,port) tuple in remote_list
        remote_list.append((addr, port))
        print("Registered remote %s:%d" % (addr, port))
        # check if it's my address and port, to find out my id
        if socket.gethostbyname(addr) == my_name and port == my_port:
            server_id = index
            print("I am server #%d" % server_id)
        index += 1
    # sort by the address and port number and return it with the server_id
    return sorted(remote_list, key=lambda tup: (tup[0],tup[1])), server_id
