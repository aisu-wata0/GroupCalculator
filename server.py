#!python

import socket
import threading
import sys

BUFSIZ = 8192
g_ThreadTCP = None
g_Host = ""


class ServerTCP(threading.Thread):
    PORT = 14699
    # Communication state constants
    REQUESTED = 0
    OK = 1
    NOK = 2
    ABORT = 3

    def __init__(self, serverId):
        threading.Thread.__init__(self)
        # Construction parameters
        self.Id = serverId
        print("Creating server #%d" % self.Id)
        sys.stdout.flush()

        print("Creating TCP socket port:%d." % ServerTCP.PORT)
        sys.stdout.flush()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Connection dictionary: [host] = connection
        self.connDic = {}

        self.queueSize = 5

    # Thread method invoked when started
    def run(self):
        global g_Host

        print("ServerTCP running ID: %s"
              % str(threading.current_thread().ident))
        sys.stdout.flush()

        print("Bind TCP %s:%d" % (g_Host, ServerTCP.PORT))
        sys.stdout.flush()
        self.socket.bind((g_Host, ServerTCP.PORT));

        print("Server listening...")
        sys.stdout.flush()
        self.socket.listen(self.queueSize)

        while True:
            try:
                # establish connection
                conn, addr = self.socket.accept()
                print("Connected %s:%d" % (str(addr[0]), addr[1]))
                sys.stdout.flush()
                self.connDic[str(addr[0])] = conn

                # send response
                msg = 'Connected to ' + g_Host + ":" + str(self.PORT) + "\r\n"
                conn.send(msg.encode('ascii'))
                # end connection
                conn.close()
                del self.connDic[str(addr[0])]
            except (KeyboardInterrupt, SystemExit):
                for connection in self.connDic:
                    connection.close()
                break


def main(argv):
    global g_Host
    global g_ThreadTCP

    g_Host = socket.gethostbyname(socket.getfqdn())

    serverId = 3
    g_ThreadTCP = ServerTCP(serverId)
    g_ThreadTCP.start()


if __name__ == "__main__":
    main(sys.argv[1:])