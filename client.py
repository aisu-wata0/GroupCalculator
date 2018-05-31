#!python
import socket
import remotes
import sys
import select

import logger

# buffer size
BUFSIZ = 8192
TIMEOUT = 4


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


def main_tcp():
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
        for idx, remote in enumerate(remote_list):
            g_ClientLog.print("[Client] Requesting server #%d" % idx)
            # tenta conectar no servidor da iteracao atual
            # non blocking
            sock = connect_server(remote)
            socks.append(sock)

        g_ClientLog.print("[Client] Waiting any server for %ds..." % TIMEOUT)
        # this will block until at least one socket is ready || Timeout
        _, ready_to_write, in_error = select.select([], socks, [], TIMEOUT)
        # if not timeout
        if ready_to_write:
            # for all those that connected
            for sock in ready_to_write:
                g_ClientLog.print("[Client] Connected to " + str(sock.getsockname()))
                g_ClientLog.print("[Client] Sending expression " + expression)
                # mensagem é codificada em ascii
                msg = expression.encode('ascii')
                # mensagem é enviada ao servidor da iteracao atual
                sock.send(msg)  # This is will not block

            g_ClientLog.print("[Client] Waiting any server result")
            # this will block until at least one socket is ready
            # wait response from one of the connections, select only from those you wrote
            ready_to_read, _, in_error = select.select(ready_to_write, [], [], TIMEOUT)

            # only the leader should be ready
            for sock in ready_to_read:
                try:
                    # mensagem é recebida com a resolução da primeira
                    sock.setblocking(1)
                    g_ClientLog.print("[Client] Receiving from " + str(sock.getsockname()))
                    result = sock.recv(BUFSIZ).decode('ascii')
                    received_result = True
                    # print expression result received from server
                    if result == "exception":
                        print("[Client] An exception was detected. Try a valid mathematical expression")
                    elif result == "zero division":
                        print("[Client] A division by zero was detected. Try a valid mathematical expression")
                    else:
                        print("result = " + result)
                    sys.stdout.flush()
                except socket.timeout:
                    g_ClientLog.print("[Client] Server received expression but didn't respond")
                    print("Server timeout, try again")
                    sys.stdout.flush()
                    pass
                except Exception as e:  # Other exception
                    g_ClientLog.print("[Client] Exception: " + str(e))

        for sock in socks:
            g_ClientLog.print("[Client] Closing socket " + str(sock.getsockname()))
            sock.close()

        if not received_result:
            g_ClientLog.print("[Client] No server could connect")
            print("All servers down")
            sys.stdout.flush()


# TCP code
MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007


def main_udp():
    # Create Loggers
    global g_ClientLog
    # serverLogFile = open("Client.log", "w")
    # g_ClientLog = logger.Logger(serverLogFile)
    g_ClientLog = logger.Logger(sys.stdout)
    g_ClientLog.header("Client")

    while True:
        # recebe a expressão aritmética do usuário.
        expression = input("Type an arithmetic expression. Example: 1+1, (13+1)*2, 5^3\n")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(TIMEOUT)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        # sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        data = expression.encode('ascii')
        sock.sendto(data, (MCAST_GRP, MCAST_PORT))
        try:
            data, addr = sock.recvfrom(1024)
            result = data.decode('ascii')

            if result == "exception":
                print("[Client] An exception was detected. Try a valid mathematical expression")
            elif result == "zero division":
                print("[Client] A division by zero was detected. Try a valid mathematical expression")
            else:
                print("result = " + result)
            sys.stdout.flush()
            print('from ' + str(addr))
        except socket.timeout:
            g_ClientLog.print("[Client] No server responded")
            print("Server timeout, try again")
            sys.stdout.flush()
        g_ClientLog.print("[ClientUDP] Closing socket " + str(sock.getsockname()))
        sock.close()


if __name__ == "__main__":
    if sys.argv.__len__() < 2:
        print("Wrong parameters! ./python3 client [TCP/UDP]")
        exit()
    if sys.argv[1].lower() == "tcp":
        main_tcp()
    elif sys.argv[1].lower() == "udp":
        main_udp()
    else:
        print("Wrong parameters! ./python3 client [TCP/UDP]")
        exit()
