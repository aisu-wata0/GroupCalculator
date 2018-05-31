#!python
import socket
import remotes
import sys
import select

import logger

# buffer size
BUFSIZ = 8192
TIMEOUT = 4

MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007

# Creates a non-blocking TCP socket file descriptor
def create_socket():
    g_ClientLog.print("[Client] Created socket")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(0)
    return sock


# This function receives a tuple (host, port) and creates a non-blocking socket attempting connection
# To use the sockets use the blocking instruction:
# ready_to_read, ready_to_write, in_error = select.select([], socks, [], TIMEOUT)
# socks is a list of sockets returned by this function
# ready_to_write will be the list of sockets in which connection was successful
# ready_to_read will be the list of sockets in which a message is ready to be read
def connect_server(remote):
    sock = create_socket()
    # Get remote info
    host, port = remote
    try:
        # get remote address
        host = socket.gethostbyname(host)
        # Tries to establish connection
        sock.connect_ex((host, port))
    except Exception as e:  # Other exception
        g_ClientLog.print("[Client] Exception: " + str(e) + " on connect server %s:%d" % (host, port))

    # return the non-blocking socket attempting connection
    return sock


def main(argv):
    # Create Loggers
    global g_ClientLog
    # serverLogFile = open("Client.log", "w")
    # g_ClientLog = logger.Logger(serverLogFile)
    g_ClientLog = logger.Logger(sys.stdout)
    g_ClientLog.header("Client")

    # remote_list returns a array of tuples (hostname, port) from servers.txt
    remote_list, _ = remotes.create_remote_list()

    while True:
        # recebe a expressão aritmética do usuário.
        expression = input("Type an arithmetic expression. Example: 1+1, (13+1)*2, 5^3\n")
        received_result = False
        # para cada endereço local do remote_list, iremos iterar.
        # tenta conectar no servidor. Se for um sucesso, ele envia a expressão
        # e aguarda o recebimento da resposta. Caso contrário, procede para a
        # próxima iteração.
        socks = []

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        # sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        data = expression.encode('ascii')
        sock.sendto(data, (MCAST_GRP, MCAST_PORT))
        try:
            data, addr = sock.recvfrom(1024)
            expression = data.decode('ascii')
            print(expression)
            print('from ' + str(addr))
        except socket.timeout:
            g_ClientLog.print("[Client] No server responded")
            print("Server timeout, try again")
            sys.stdout.flush()
        g_ClientLog.print("[ClientUDP] Closing socket " + str(sock.getsockname()))
        sock.close()


if __name__ == "__main__":
    main(sys.argv[0:])
