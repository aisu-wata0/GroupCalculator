#!python

import socket
import threading
import sys
import time

BUFSIZ = 8192
g_ThreadTCP = None
g_Host = ""


class ServeClient(threading.Thread):
    def __init__(self, conn, addr):
        threading.Thread.__init__(self)
        # Construction parameters
        self.conn = conn
        self.addr = addr

    # Thread method invoked when started
    def run(self):
        # send response
        msg = "response" + "\r\n"
        self.conn.send(msg.encode('ascii'))
        # end connection
        self.conn.close()


class ServerTCP(threading.Thread):
    def __init__(self, serverId, port):
        threading.Thread.__init__(self)
        # Construction parameters
        self.Id = serverId
        self.port = port
        # client thread array
        # self.clients = []
        print("Creating server #%d" % self.Id)
        sys.stdout.flush()

        print("Creating TCP socket port:%d." % self.port)
        sys.stdout.flush()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.queueSize = 5

    # Thread method invoked when started
    def run(self):
        global g_Host

        print("ServerTCP running ID: %s"
              % str(threading.current_thread().ident))
        sys.stdout.flush()

        print("Bind TCP %s:%d" % (g_Host, self.port))
        sys.stdout.flush()
        self.socket.bind((g_Host, self.port));

        print("Server listening...")
        sys.stdout.flush()
        self.socket.listen(self.queueSize)

        while True:
            # establish connection
            conn, addr = self.socket.accept()
            print("Connected %s:%d" % (str(addr[0]), addr[1]))
            sys.stdout.flush()
            # send response
            msg = 'Connected to ' + g_Host + ":" + str(self.port) + "\r\n"
            conn.send(msg.encode('ascii'))

            client = ServeClient(conn, str(addr[0]))
            client.start()


def main(argv):
    global g_Host
    global g_ThreadTCP

    g_Host = socket.gethostbyname(socket.getfqdn())

    serverId = 3
    g_ThreadTCP = ServerTCP(serverId, 14699)
    g_ThreadTCP.start()


if __name__ == "__main__":
    main(sys.argv[1:])