#!python
import socket
import remotes
import sys
import select
from abc import abstractmethod

import logger

# buffer size
BUFSIZ = 8192
TIMEOUT = 4

MCAST_GRP = '224.1.1.1'
MCAST_PORT = 5007


# Creates a non-blocking TCP socket file descriptor
def create_socket():
    g_ClientLog.print("[ClientTCP] Created socket")
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
        sock.connect((host, port))
    except BlockingIOError:
        g_ClientLog.print("[ClientTCP] Non-blocking connection in progress...")
        pass
    except Exception as e:  # Other exception
        g_ClientLog.print("[ClientTCP] Exception: " + str(e) + " on connect server %s:%d" % (host, port))

    # return the non-blocking socket attempting connection
    return sock


class Client:
    # Attempts to send a expression to server group
    # Opens needed sockets
    # There are no guarantees that the server received it
    # the timeout job is left to receive_result()
    @abstractmethod
    def send_exp(self, expression):
        pass

    # Blocks until a response is received || Timeout
    @abstractmethod
    def receive_result(self):
        pass

    # Closes sockets
    @abstractmethod
    def close(self):
        pass


class ClientTCP(Client):
    def __init__(self, remote_list):
        self.remote_list = remote_list
        self.sent_socks = []
        self.socks = []

    # Blocks to connect to servers || Timeout
    # If any connected
    #   sends them the data without blocking
    def send_exp(self, expression):
        # para cada endereço local do remote_list, iremos iterar.
        # tenta conectar no servidor. Se for um sucesso, ele envia a expressão
        # e aguarda o recebimento da resposta. Caso contrário, procede para a
        # próxima iteração.
        self.socks = []
        for idx, remote in enumerate(self.remote_list):
            g_ClientLog.print("[ClientTCP] Requesting server #%d" % idx)
            # tenta conectar no servidor da iteracao atual
            # non blocking
            sock = connect_server(remote)
            self.socks.append(sock)

        g_ClientLog.print("[ClientTCP] Waiting any server for %ds..." % TIMEOUT)
        # this will block until at least one socket is ready to write || Timeout
        _, ready_to_write, in_error = select.select([], self.socks, [], TIMEOUT)

        self.sent_socks = []
        # if not timeout
        if ready_to_write:
            # for all those that connected
            for sock in ready_to_write:
                g_ClientLog.print("[ClientTCP] Connected to " + str(sock.getsockname()))
                g_ClientLog.print("[ClientTCP] Sending expression: " + expression)
                # mensagem é codificada em ascii
                data = expression.encode('ascii')
                try:
                    # mensagem é enviada ao servidor da iteracao atual
                    sock.send(data)  # This is will not block
                    self.sent_socks.append(sock)
                except Exception as e:
                    g_ClientLog.print("[ClientTCP] Exception in send: " + str(e))
                    pass

    # If you tried to send to a connected server,
    #   blocks until socket is ready to be read || Timeout
    def receive_result(self):
        # if you actually sent something
        if self.sent_socks:
            g_ClientLog.print("[ClientTCP] Waiting any server result")
            # this will block until at least one socket is ready to read
            # wait response from one of the connections, select only from those you wrote
            ready_to_read, _, in_error = select.select(self.sent_socks, [], [], TIMEOUT)
            # only the leader should be ready
            for sock in ready_to_read:
                result = sock.recv(BUFSIZ).decode('ascii')
                g_ClientLog.print("[ClientTCP] Receiving from " + str(sock.getsockname()))
                return result
        else:
            raise socket.timeout

    def close(self):
        for sock in self.socks:
            g_ClientLog.print("[ClientTCP] Closing socket " + str(sock.getsockname()))
            sock.close()


class ClientUDP(Client):
    def __init__(self):
        self.sock = None

    # Sends a non-blocking multicast
    def send_exp(self, expression):
        g_ClientLog.print("[ClientUDP] Creating socket")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.settimeout(TIMEOUT)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        # sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        g_ClientLog.print("[ClientUDP] Multicasting " + str((MCAST_GRP, MCAST_PORT)) + " expression: " + expression)
        data = expression.encode('ascii')
        self.sock.sendto(data, (MCAST_GRP, MCAST_PORT))

    # Waits for a server response || Timeout
    def receive_result(self):
        g_ClientLog.print("[ClientUDP] Waiting any server for %ds..." % TIMEOUT)
        data, addr = self.sock.recvfrom(BUFSIZ)
        g_ClientLog.print("[ClientUDP] Received from " + str(addr))
        result = data.decode('ascii')
        return result

    def close(self):
        self.sock.close()


def main(argv):
    global client

    def err():
        print("Usage: %s [TCP/UDP]" % argv[0])
        sys.exit()

    if len(sys.argv) == 2:
        if sys.argv[1].lower() == "tcp":
            # remote_list returns a array of tuples (hostname, port) from servers.txt
            remote_list, _ = remotes.create_remote_list()
            client = ClientTCP(remote_list)
        elif sys.argv[1].lower() == "udp":
            client = ClientUDP()
        else:
            err()
    else:
        err()

    # Create Loggers
    global g_ClientLog
    # serverLogFile = open("Client.log", "w")
    # g_ClientLog = logger.Logger(serverLogFile)
    g_ClientLog = logger.Logger(sys.stdout)
    g_ClientLog.header("Client")

    while True:
        # recebe a expressão aritmética do usuário.
        expression = input("Type an arithmetic expression. Example: 1+1, (13+1)*2, 5^3\n")

        client.send_exp(expression)

        received_result = False
        try:
            result = client.receive_result()
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
            g_ClientLog.print("[Client] Timeout")
            print("Server timeout, try again")
            sys.stdout.flush()
            pass
        except Exception as e:  # Other exception
            g_ClientLog.print("[Client] Exception: " + str(e))

        if not received_result:
            g_ClientLog.print("[Client] No server could respond")
            print("No response")
            sys.stdout.flush()

        client.close()


if __name__ == "__main__":
    main(sys.argv[0:])
