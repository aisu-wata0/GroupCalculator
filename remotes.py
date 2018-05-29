#!python

import socket


def create_remote_list(argvi, g_Host):
    remoteList = []
    index = 0
    serverId = 0
    myPort = int(argvi)
    file = open("servers.txt", "r")
    for line in file:
        lineArr = line.split(" ")
        addr = lineArr[0]
        port = int(lineArr[1])
        remoteList.append((addr, port))
        print("Registered remote %s:%d" % (addr, port))
        if socket.gethostbyname(addr) == g_Host and port == myPort:
            serverId = index
            port = remoteList[index][1]
            print("I am server #%d" % serverId)
        index += 1

    return {'remoteList': remoteList, "serverId": serverId, "myPort" : myPort}
