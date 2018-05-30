#!python
import socket
import remotes
import sys
import select

import logger

# buffer size
BUFSIZ = 8192


# Creates a TCP socket file descriptor with timeout
def create_socket():
    g_ClientLog.print("[Client] Created socket")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    return sock


# Essa função recebe uma tuple (host, porta) cria um socket e tenta fazer uma conexão.
# Caso a conexão ocorra, a função retorna True e o socket (que será usado posteriormente).
# Caso ocorra uma exceção durante a conexão, fecha o socket
# e retorna False e o socket fechado, que não será mais usado.
def connect_server(remote):
    is_connected = False

    sock = create_socket()
    # Get remote info
    host, port = remote

    try:
        # get remote address
        host = socket.gethostbyname(host)
        # Tries to establish connection
        # if refused, ConnectionRefusedError exception will be thrown.
        sock.connect((host, port))
        g_ClientLog.print("[Client] Connected: server %s:%d" % (host, port))
        # Connection successful
        is_connected = True  # set return value
    except ConnectionRefusedError:
        # Connection refused
        g_ClientLog.print("[Client] Refused: server %s:%d" % (host, port))
        pass
    except Exception as e:  # Other exception
        g_ClientLog.print("[Client] Exception: " + str(e) + " for server %s:%d" % (host, port))
    finally:
        # If the socket couldn't connect, close it
        if not is_connected:
            g_ClientLog.print("[Client] Closing socket")
            sock.close()

        # Return (success, socket)
        # if successful, socket can be used to send/receive messages
        return is_connected, sock


def main(argv):
    # remote_list returns a array of tuples (hostname, port) from servers.txt
    remote_list, _ = remotes.create_remote_list()

    # Create Loggers
    global g_ClientLog
    # serverLogFile = open("Client.log", "w")
    # g_ClientLog = logger.Logger(serverLogFile)
    g_ClientLog = logger.Logger(sys.stdout)
    g_ClientLog.header("Client")

    while True:
        # recebe a expressão aritmética do usuário.
        expression = input("Type an arithmetic expression. Example: 1+1, (13+1)*2, 5^3\n")

        # para cada endereço local do remote_list, iremos iterar.
        # tenta conectar no servidor. Se for um sucesso, ele envia a expressão
        # e aguarda o recebimento da resposta. Caso contrário, procede para a
        # próxima iteração.
        is_connected = False
        shouldloop = True

        socketlist = []
        for idx, remote in enumerate(remote_list):
            is_connected, sock = connect_server(remote)
            if is_connected:
                g_ClientLog.print("[Client] Sending expression " + expression)

                # mensagem é codificada em ascii
                msg = expression.encode('ascii')

                # mensagem é enviada ao servidor da iteracao atual
                sock.send(msg)
                socketlist.append(sock)

        while shouldloop:
            # this will block until at least one socket is ready
            ready_socks, _, _ = select.select(socketlist, [], [])
            for sock in ready_socks:
                shouldloop = False

                # outra mensagem é recebida com a resolução da primeira e decodificada
                try:
                    data, addr = sock.recvfrom(BUFSIZ)  # This is will not block
                    result = data.decode('ascii')
                    print("received message:", result)

                    # print expression result received from server
                    if result == "exception":
                        print("[Client] An exception was detected. Try a valid mathematical expression")
                    elif result == "zero division":
                        print("[Client] A division by zero was detected. Try a valid mathematical expression")
                    else:
                        print("result = " + result)

                    sys.stdout.flush()
                except socket.timeout:
                    g_ClientLog.print("[Client] Server connected but didn't respond")
                    print("Server timeout, try again")
                    sys.stdout.flush()
                    pass
                except Exception as e:  # Other exception
                    g_ClientLog.print("[Client] Exception: " + str(e))
                finally:
                    g_ClientLog.print("[Client] Closing socket")
                    sock.close()
        if socketlist is []:
            g_ClientLog.print("[Client] No server could connect")
            print("All servers down")
            sys.stdout.flush()


if __name__ == "__main__":
    main(sys.argv[0:])
