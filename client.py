#!python
import socket
import remotes
import sys

BUFSIZ = 1024


def create_socket():
    sock = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    return sock

def connect_server(remote, entrada):
    is_connected = False
    sock = create_socket()
    host = remote[0]
    port = remote[1]

    try:
        host = socket.gethostbyname(host)

        sock.connect((host, port))
        print("[Client] Connected: server %s:%d" % (host, port))

        mensagem = entrada.encode('ascii')
        sock.send(mensagem)

        sock.recvfrom(port) #receive initial value from server

        is_connected = True

    except ConnectionRefusedError:
        print("[Client] Refused:   server %s:%d" % (host, port))
        pass
    except Exception as e:
        print(e)
    finally:
        if not is_connected:
            print("[Client] Closing socket")
            sock.close()
        return is_connected, sock


def main(argv):
    remote_list, _ = remotes.create_remote_list()

    while True:
        get_input = input("Type an arithmetic expression. Example: 1+1, 8/2, 5*3")

        for idx, remote in enumerate(remote_list):
            print("[Client] Requesting server #%d" % idx)
            is_connected, sock = connect_server(remote, get_input)
            if is_connected:
                print("[Client] Received " + sock.recv(BUFSIZ).decode('ascii') + " from Server")
                print("[Client] Closing socket")
                sock.close()


if __name__ == "__main__":
    main(sys.argv[0:])
