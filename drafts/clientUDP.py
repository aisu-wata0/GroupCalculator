#!python

import socket

MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
    # sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

    sock.sendto("robot".encode('ascii'), (MCAST_GRP, MCAST_PORT))
    print(sock.getsockname())
    data, addr = sock.recvfrom(1024)
    print(data.decode('ascii'))
    print('from ' + str(addr))


if __name__ == '__main__':
    main()