#!python

import socket


def create_remote_list(my_port, my_name):
    remote_list = []
    index = 0
    server_id = 0
    file = open("servers.txt", "r")
    for line in file:
        line_split = line.split(" ")
        addr = line_split[0]
        port = int(line_split[1])
        remote_list.append((addr, port))
        print("Registered remote %s:%d" % (addr, port))
        if socket.gethostbyname(addr) == my_name and port == my_port:
            server_id = index
            print("I am server #%d" % server_id)
        index += 1

    return {'remote_list': remote_list, "server_id": server_id}
