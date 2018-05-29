#!python
import socket
import remotes
import server
import sys

PORT = 14699
BUFSIZ = 1024

# create socket
sock = socket.socket(
    socket.AF_INET, socket.SOCK_STREAM)

host = socket.gethostbyname(socket.getfqdn())
sock.close()
remote = remotes.create_remote_list(PORT, host)
remotelist = remote['remoteList']
myport = remote['myPort']


def create_socket():
    sock = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    return sock


def check_if_connection_is_fine(porta):
    sock = create_socket()
    diditwork = False
    try:
        sock.connect((host, porta))
        # send my id as heartbeat
        # msg = "rarwrrr"
        # sock.send(msg.encode('ascii'))
        diditwork = True
        print("[Remote %d] Worked heartbeat" % porta)
    except ConnectionRefusedError:
        print("[Remote %d] Refused heartbeat" % porta)
        diditwork = False
        pass
    except Exception as e:
        print(e)
    finally:
        print("[Remote %d] Closing socket" % porta)
        sys.stdout.flush()
        sock.close()
        return diditwork


for idx, remote in enumerate(remotelist):
    addr = remote[0]
    port = remote[1]
    print(port)

    remote = server.Remote(addr, port, idx)
    is_connection_working = check_if_connection_is_fine(remote.port)
    if is_connection_working:
        print("Connection is working with: " + remote.port.__str__())
        break
