#!python

import socket
import threading
from threading import Timer
import sys
import struct
from datetime import datetime
import select
import time

BUFSIZ = 8192
g_heartbeatInterval = 4
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
        print("[ServerTCP] Creating server #%d" % self.Id)
        sys.stdout.flush()

        print("[ServerTCP] Creating TCP socket")
        sys.stdout.flush()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.queueSize = 5

    # Thread method invoked when started
    def run(self):
        global g_Host
        print("[ServerTCP] Bind TCP %s:%d" % (g_Host, self.port))
        sys.stdout.flush()
        self.socket.bind((g_Host, self.port));

        print("[ServerTCP] listening...")
        sys.stdout.flush()
        self.socket.listen(self.queueSize)

        while True:
            # establish connection
            conn, addr = self.socket.accept()
            print("[ServerTCP] Connected %s:%d" % (str(addr[0]), addr[1]))
            sys.stdout.flush()
            if g_HealthMonitor.leader() == self.Id:
                # send response
                msg = 'Connected to ' + g_Host + ":" + str(self.port) + "\r\n"
                conn.send(msg.encode('ascii'))

                client = ServeClient(conn, str(addr[0]))
                client.start()

    # heartbeat port
    def portHB(self):
        return self.port + 1


class RepeatedTimer(object):
    def __init__(self, interval, fun, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.fun = fun
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.fun(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


class Heartbeat:
    def __init__(self, remote):
        global g_heartbeatInterval

        self.remote = remote
        print("[Remote %d] Creating socket" % remote.Id)
        sys.stdout.flush()

        print("[Remote %d] Starting heartbeat" % remote.Id)
        sys.stdout.flush()
        self.hb = RepeatedTimer(g_heartbeatInterval, self.heartbeat)

    def createSocket(self):
        global g_heartbeatInterval

        sock_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # set timeout
        secs = int(self.timeout())
        micro_secs = int(0)
        timeval = struct.pack('ll', secs, micro_secs)
        sock_fd.setsockopt(socket.SOL_SOCKET, socket.SO_SNDTIMEO, timeval)
        return sock_fd

    def heartbeat(self):
        global g_heartbeatInterval

        host = socket.gethostbyname(self.remote.addr)
        print("[Remote %d] Sending heartbeat %s:%d" % (self.remote.Id, host, self.remote.portHB()))
        sys.stdout.flush()
        sock_fd = self.createSocket()
        sock_fd.settimeout(self.timeout())
        try:
            sock_fd.connect((host, self.remote.portHB()))
            # send my id as heartbeat
            msg = str(g_ThreadTCP.Id)
            sock_fd.send(msg.encode('ascii'))
        except ConnectionRefusedError:
            print("[Remote %d] Refused heartbeat" % self.remote.Id)
            pass
        finally:
            print("[Remote %d] Closing socket" % self.remote.Id)
            sys.stdout.flush()
            sock_fd.close()

    def timeout(self):
        global g_heartbeatInterval
        return int(g_heartbeatInterval/2)

class Remote:
    def __init__(self, addr, port, Id):
        self.addr = addr
        self.port = port
        self.Id = Id
        print("[Remote %d] created" % self.Id)
        sys.stdout.flush()
        self.delta = 0
        self.lastHeartbeat = datetime.now()

    # heartbeat port
    def portHB(self):
        return self.port + 1


class HealthMonitor(threading.Thread):
    def __init__(self, remoteList):
        threading.Thread.__init__(self)
        self.remotes = []

        print("[HealthMonitor] started thread %s" % str(threading.current_thread().ident))
        sys.stdout.flush()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.queueSize = len(remoteList)*3

        heartbeatList = []
        # Construction parameters
        for idx, remote in enumerate(remoteList):
            addr = remote[0]
            port = remote[1]
            remote = Remote(addr, port, idx)
            self.remotes.append(remote)
            if idx != g_ThreadTCP.Id:
                heartbeatList.append(Heartbeat(remote))

    # Thread method invoked when started
    def run(self):
        print("[HealthMonitor] Bind TCP %s:%d" % (g_Host, g_ThreadTCP.portHB()))
        sys.stdout.flush()
        self.socket.bind((g_Host, g_ThreadTCP.portHB()))

        print("[HealthMonitor] listening for heartbeats...")
        sys.stdout.flush()
        self.socket.listen(self.queueSize)

        while True:
            # receive heartbeats
            conn, addr = self.socket.accept()
            print("[HealthMonitor] Connected %s:%d" % (str(addr[0]), addr[1]))
            sys.stdout.flush()
            data = conn.recv(BUFSIZ)
            # heartbeat has the server id
            idx = data.decode('ascii')
            print("[HealthMonitor] Heartbeat from %s" % idx)
            sys.stdout.flush()
            idx = int(idx)
            # Calculate time since last heartbeat from this server
            last = self.remotes[idx].lastHeartbeat
            # update heartbeat time
            self.remotes[idx].lastHeartbeat = datetime.now()
            time_delta = self.remotes[idx].lastHeartbeat - last
            delta = time_delta.total_seconds() * 1000
            delta += time_delta.microseconds / 1000
            self.remotes[idx].delta = delta
            print("[HealthMonitor] Server %d heartbeat, delta = %dms" % (idx, delta))
            sys.stdout.flush()
            conn.close()

    def leader(self):
        global g_heartbeatInterval

        for re in self.remotes:
            if re.delta <= g_heartbeatInterval+g_heartbeatInterval/2:
                print("[HealthMonitor] Leader is %d" % re.Id)
                sys.stdout.flush()
                return re.Id
        return -1  # should be impossible, local server delta = 0


def main(argv):
    global g_Host
    global g_ThreadTCP
    global g_HealthMonitor

    g_Host = socket.gethostbyname(socket.getfqdn())

    if len(argv) < 2:
        print("Hostname: %s" % g_Host)
        print("Usage %s [port]" % argv[0])
        exit(0)

    remoteList = []
    index = 0
    serverId = 0
    myPort = int(argv[1])
    file = open("servers.txt", "r")
    for line in file:
        lineArr = line.split(" ")
        addr = lineArr[0]
        port = int(lineArr[1])
        remoteList.append((addr, port))
        print("Registered remote %s:%d" % (addr, port))
        if socket.gethostbyname(addr) == g_Host and port == myPort:
            serverId = index
            port = remoteList[index][1]
            print("I am server #%d" % serverId)
        index += 1

    g_ThreadTCP = ServerTCP(serverId, myPort)
    g_ThreadTCP.start()

    g_HealthMonitor = HealthMonitor(remoteList)
    g_HealthMonitor.start()


if __name__ == "__main__":
    main(sys.argv[0:])