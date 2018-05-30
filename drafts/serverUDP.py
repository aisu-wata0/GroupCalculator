#!python

import socket
import binascii

MULTICAST_GRP = '224.1.1.1'
MULTICAST_PORT = 5007


def main():
    host = socket.gethostbyname(socket.getfqdn())

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except AttributeError:
        pass
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

    sock.bind(('', MULTICAST_PORT))
    # sock.bind((MULTICAST_GRP, MULTICAST_PORT))

    mreq = socket.inet_aton(MULTICAST_GRP) + socket.inet_aton(host)
    # mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GRP), socket.INADDR_ANY)

    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(host))
    sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        print("listening...")
        try:
            data, addr = sock.recvfrom(1024)
            print(data.decode('ascii'))
        except Exception as e:  # Other exception
            print('Exception' % str(e))
            hex_data = binascii.hexlify(data)
            print('Data = %s' % hex_data)


if __name__ == '__main__':
    main()