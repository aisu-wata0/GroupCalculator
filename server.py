#!python

import socket
import threading
from threading import Timer
import sys
import struct
import datetime
import remotes
import pyparsingtest

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
        # receive expression
        expression = self.conn.recv(BUFSIZ).decode('ascii')
        # calculate result
        result = pyparsingtest.create_result(expression)
        print("received: " + expression + " result: " + str(result))
        sys.stdout.flush()
        # respond result
        self.conn.send(str(result).encode("ascii"))
        # end connection
        self.conn.close()


class ServerTCP(threading.Thread):
    def __init__(self, server_id, port):
        threading.Thread.__init__(self)
        # Construction parameters
        self.Id = server_id
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
        self.socket.bind((g_Host, self.port))

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
                # msg = 'Connected to ' + g_Host + ":" + str(self.port) + "\r\n"
                # conn.send(msg.encode('ascii'))

                client = ServeClient(conn, addr[0])
                client.start()

    # heartbeat port
    def port_heart(self):
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


# Tries to send heartbeats to the remote continuously by the interval constant defined
class Heartbeat:
    def __init__(self, remote):
        global g_heartbeatInterval

        self.remote = remote
        print("[Remote %d] Creating socket" % remote.Id)
        sys.stdout.flush()

        print("[Remote %d] Starting heartbeat" % remote.Id)
        sys.stdout.flush()
        self.hb = RepeatedTimer(g_heartbeatInterval, self.heartbeat)

    def heartbeat(self):
        global g_heartbeatInterval

        host = socket.gethostbyname(self.remote.addr)
        print("[Remote %d] Sending heartbeat %s:%d" % (self.remote.Id, host, self.remote.port_heart()))
        sys.stdout.flush()
        sock_fd = Heartbeat.create_socket()
        sock_fd.settimeout(self.timeout())
        try:
            sock_fd.connect((host, self.remote.port_heart()))
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

    @staticmethod
    def create_socket():
        global g_heartbeatInterval

        sock_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # set timeout
        secs = int(Heartbeat.timeout())
        micro_secs = int(0)
        timeval = struct.pack('ll', secs, micro_secs)
        sock_fd.setsockopt(socket.SOL_SOCKET, socket.SO_SNDTIMEO, timeval)
        return sock_fd

    @staticmethod
    def timeout():
        global g_heartbeatInterval
        return int(g_heartbeatInterval / 2)


# Stores information of other remotes
class Remote:
    def __init__(self, addr, port, idx):
        self.addr = addr
        self.port = port
        self.Id = idx
        print("[Remote %d] created" % self.Id)
        sys.stdout.flush()
        self.devHB = 0
        self.lastHeartbeat = datetime.datetime.now()

    # heartbeat port
    def port_heart(self):
        return self.port + 1


def timedelta_ms(timedelta):
    delta_ms = timedelta.total_seconds() * 1000
    delta_ms += timedelta.microseconds / 1000
    return delta_ms


# Monitors other remotes by listening heartbeats, creates Heartbeats to inform others
class HealthMonitor(threading.Thread):
    def __init__(self, remote_list):
        threading.Thread.__init__(self)
        print("[HealthMonitor] created thread %s" % str(threading.current_thread().ident))
        sys.stdout.flush()

        # remote array
        self.remotes = []
        # create socket
        self.socketListenHeartbeats \
            = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socketListenHeartbeats\
            .setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # heartbeat queue size
        self.queueSize = len(remote_list)*3

        # Heartbeat sending list
        heartbeat_list = []
        # Construct remotes and Heartbeat list
        for idx, remote in enumerate(remote_list):
            addr = remote[0]
            port = remote[1]
            # create remote info
            remote = Remote(addr, port, idx)
            # add to list
            self.remotes.append(remote)
            # If not myself, send heartbeats to it
            if idx != g_ThreadTCP.Id:
                # create and add Heartbeat
                heartbeat_list.append(Heartbeat(remote))

    # Thread method invoked when started
    def run(self):
        print("[HealthMonitor] Bind TCP %s:%d" % (g_Host, g_ThreadTCP.port_heart()))
        sys.stdout.flush()
        # receive from any source, in 'portHG()' port
        self.socketListenHeartbeats.bind((g_Host, g_ThreadTCP.port_heart()))

        print("[HealthMonitor] listening for heartbeats...")
        sys.stdout.flush()
        self.socketListenHeartbeats.listen(self.queueSize)

        while True:
            # accept connection
            conn, addr = self.socketListenHeartbeats.accept()
            print("[HealthMonitor] Connected %s:%d" % (str(addr[0]), addr[1]))
            sys.stdout.flush()
            # receive heartbeat
            data = conn.recv(BUFSIZ)
            # heartbeat has the server id
            idx = data.decode('ascii')
            print("[HealthMonitor] Heartbeat from %s" % idx)
            sys.stdout.flush()
            idx = int(idx)
            # Calculate delta time since last heartbeat from this server
            prev = self.remotes[idx].lastHeartbeat
            # update heartbeat time
            self.remotes[idx].lastHeartbeat = datetime.datetime.now()
            timedelta = self.remotes[idx].lastHeartbeat - prev
            # update deviation
            dev = 0.75*self.remotes[idx].devHB\
                + 0.25 * abs(timedelta_ms(timedelta) - 1000*g_heartbeatInterval)
            self.remotes[idx].devHB = dev
            print("[HealthMonitor] Server %d heartbeat, delta = %dms; dev = %d"
                  % (idx, timedelta_ms(timedelta), self.remotes[idx].devHB))
            sys.stdout.flush()
            # close connection
            conn.close()

    def leader(self):
        global g_heartbeatInterval
        print("[HealthMonitor] leader calc")
        sys.stdout.flush()
        # calculate tolerance
        now = datetime.datetime.now()
        # return first remote Id considered available
        for re in self.remotes:
            if re.Id == g_ThreadTCP.Id:  # local
                print("[HealthMonitor] Leader is %d, me" % re.Id)
                sys.stdout.flush()
                return re.Id
            timeout = datetime.timedelta(milliseconds=int(1000 * g_heartbeatInterval + 4 * re.devHB))
            print("[HealthMonitor] %d timeoutInterval = %dms" % (re.Id, 1000*timeout.total_seconds()))
            tolerance = now - timeout
            last = re.lastHeartbeat
            delta = timedelta_ms(last - tolerance)
            print("[HealthMonitor] %d delta = %dms" % (re.Id, delta))
            sys.stdout.flush()
            # inside tolerance
            if delta > 0:  # TODO test this
                print("[HealthMonitor] Leader is %d" % re.Id)
                sys.stdout.flush()
                return re.Id
        return -1  # should be impossible, local server delta = 0


def main(argv):
    global g_Host
    global g_ThreadTCP
    global g_HealthMonitor

    # get my host
    g_Host = socket.gethostbyname(socket.getfqdn())

    # check parameters
    if len(argv) < 2:
        print("Hostname: %s" % g_Host)
        print("Usage %s [port]" % argv[0])
        exit(0)
    # get parameters
    my_port = int(argv[1])

    # get remotes registered
    remote_list, server_id = remotes.create_remote_list(my_port, g_Host)

    # Start Server
    g_ThreadTCP = ServerTCP(server_id, my_port)
    g_ThreadTCP.start()

    # Start HealthMonitor
    g_HealthMonitor = HealthMonitor(remote_list)
    g_HealthMonitor.start()


if __name__ == "__main__":
    main(sys.argv[0:])
