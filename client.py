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


def connect_server(remote):
    is_connected = False
    sock = create_socket()
    host = remote[0]
    port = remote[1]
    try:
        host = socket.gethostbyname(host)
        sock.connect((host, port))
        is_connected = True
        print("[Client] Connected: server %s:%d" % (host, port))
        sys.stdout.flush()
    except ConnectionRefusedError:
        print("[Client] Refused:   server %s:%d" % (host, port))
        sys.stdout.flush()
        pass
    except Exception as e:
        print(e)
        sys.stdout.flush()
    finally:
        if not is_connected:
            print("[Client] Closing socket")
            sys.stdout.flush()
            sock.close()
        return is_connected, sock


def main(argv):
    remote_list, _ = remotes.create_remote_list()

    for idx, remote in enumerate(remote_list):
        print("[Client] Requesting server #%d" % idx)
        sys.stdout.flush()
        is_connected, conn = connect_server(remote)
        if is_connected:
            # TODO
            # conn.send("myString")
            break


if __name__ == "__main__":
    main(sys.argv[0:])
