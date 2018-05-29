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


# def listen(sock):
#     while True:
#         try:
#             sock.settimeout(3)
#             dat, address = sock.recv(BUFSIZ)
#             return dat
#         except socket.timeout:
#             return 0


def connect_server(remote):
    is_connected = False
    sock = create_socket()
    host = remote[0]
    port = remote[1]

    try:
        host = socket.gethostbyname(host)

        sock.connect((host, port))
        print("[Client] Connected: server %s:%d" % (host, port))

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
        # read expression from user
        expression = input("Type an arithmetic expression. Example: 1+1, (13+1)*2, 5^3\n")

        # try to connect to each server
        for idx, remote in enumerate(remote_list):
            print("[Client] Requesting server #%d" % idx)
            sys.stdout.flush()
            # try server
            is_connected, sock = connect_server(remote)
            if is_connected:
                msg = expression.encode('ascii')
                print("[Client] Sending expression " + expression)
                sys.stdout.flush()
                sock.send(msg)
                print("[Client] Waiting server result")
                sys.stdout.flush()
                result = sock.recv(BUFSIZ).decode('ascii')
                print("[Client] Closing socket")
                sys.stdout.flush()
                sock.close()
                print("result = " + result)


if __name__ == "__main__":
    main(sys.argv[0:])
