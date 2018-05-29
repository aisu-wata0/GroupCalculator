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


def check_if_connection_is_fine(remote):
    did_it_work = False
    sock = create_socket()
    host = remote[0]
    port = remote[1]
    try:
        host = socket.gethostbyname(host)
        sock.connect((host, port))
        did_it_work = True
        print("[Client] Connected:\tserver %s:%d" % (host, port))
        sys.stdout.flush()
    except ConnectionRefusedError:
        print("[Client] Refused:  \tserver %s:%d" % (host, port))
        sys.stdout.flush()
        pass
    except Exception as e:
        print(e)
        sys.stdout.flush()
    finally:
        print("[Client] Closing socket")
        sys.stdout.flush()
        sock.close()
        return did_it_work


def main(argv):
    re = remotes.create_remote_list(-1, "")

    remote_list = re['remote_list']

    for idx, remote in enumerate(remote_list):
        print("[Client] Requesting server #%d" % idx)
        sys.stdout.flush()
        is_connection_working = check_if_connection_is_fine(remote)
        if is_connection_working:
            break


if __name__ == "__main__":
    main(sys.argv[0:])