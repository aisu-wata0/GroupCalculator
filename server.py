#!python

import socket
import threading
from threading import Timer
import sys
import struct
import datetime
import parse
from abc import ABC, abstractmethod

import remotes
import logger

# buffer size
BUFSIZ = 8192
g_heartbeatInterval = 4

g_ServerTCP = None
g_ServerUDP = None
g_HealthMonitor = None

g_Host = ""
MULTICAST_GRP = '224.1.1.1'
MULTICAST_PORT = 5007

g_ServerLog = None
g_HealthMonitorLog = None
g_HeartbeatLog = None


class Client(threading.Thread):
    def __init__(self, connection):
        threading.Thread.__init__(self)
        # Construction parameters
        sock, addr = connection
        self.sock = sock
        self.addr = addr
        g_ServerLog.print("[Client %s] Started" % str(self.addr))

    # Thread method invoked when started
    def run(self):
        # receive expression
        expression = self.receive_exp()

        # calculate result
        g_ServerLog.print("[Client %s] Calculating expression: %s"
                          % (str(self.addr), expression))
        message = ""
        try:
            result = parse.create_result(expression)
            g_ServerLog.print("[Client %s] result = %s" % (str(self.addr), result))
            print("received: " + str(expression) + " result: " + str(result))
            message = str(result)
        except ZeroDivisionError:
            print("received: Error! Division by Zero!")
            message = "zero division"
            pass
        except Exception as e:  # Other exception
            g_ServerLog.print(
                "[Client %s] Exception %s" % (str(self.addr), e))
            print("received: Error! Invalid expression!")
            message = "exception"
        finally:
            sys.stdout.flush()
            # respond with the result
            self.respond(message)
            # end connection
            self.sock.close()

    @abstractmethod
    def receive_exp(self):
        pass

    @abstractmethod
    def respond(self, msg):
        pass


class ClientTCP(Client):
    def receive_exp(self):
        g_ServerLog.print("[ClientTCP %s] Waiting expression" % str(self.addr))
        expression = self.sock.recv(BUFSIZ).decode('ascii')
        return expression

    # respond with the result
    def respond(self, msg):
        g_ServerLog.print(
            "[ClientTCP %s] Sending result = %s" % (str(self.addr), msg))
        self.sock.send(msg.encode("ascii"))


class ClientUDP(Client):
    def __init__(self, connection):
        super().__init__(connection)
        # Construction parameters
        self.expression = self.sock.decode('ascii')
        # create another socket to respond
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except AttributeError:
            pass

    def receive_exp(self):
        return self.expression

    # respond with the result
    def respond(self, msg):
        g_ServerLog.print(
            "[ClientUDP %s] Sending result = %s" % (str(self.addr), msg))
        self.sock.sendto(msg.encode('ascii'), self.addr)


class Server(threading.Thread):
    def __init__(self, server_id, port):
        threading.Thread.__init__(self)
        # Construction parameters
        self.Id = server_id
        self.port = port
        g_ServerLog.print("[ServerTCP] Creating server #%d" % self.Id)
        # client thread array
        # self.clients = []
        # Listening socket
        self.socket = self.create_socket()
        self.queueSize = 5

    @abstractmethod
    def create_socket(self):
        pass

    # Thread method invoked when started
    def run(self):
        global g_Host
        global g_ServerLog

        self.start_listening()

        while True:
            # establish connection
            connection = self.wait_client()
            if g_HealthMonitor.leader() == self.Id:
                client = self.create_client(connection)
                client.start()

    @abstractmethod
    def start_listening(self):
        pass

    @abstractmethod
    def wait_client(self):
        pass

    @abstractmethod
    def create_client(self, connection):
        pass

    # heartbeat port
    def port_heart(self):
        return self.port + 1


class ServerTCP(Server):
    def create_socket(self):
        g_ServerLog.print("[ServerTCP] Creating TCP socket")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock

    def start_listening(self):
        g_ServerLog.print("[ServerTCP] Bind TCP %s:%d" % (g_Host, self.port))
        self.socket.bind((g_Host, self.port))

        g_ServerLog.print("[ServerTCP] listening...")
        self.socket.listen(self.queueSize)

    def wait_client(self):
        connection = sock, addr = self.socket.accept()
        g_ServerLog.print("[ServerTCP] Connected %s:%d" % (str(addr[0]), addr[1]))
        return connection

    def create_client(self, connection):
        return ClientTCP(connection)


class ServerUDP(Server):
    def create_socket(self):
        g_ServerLog.print("[ServerUDP] Creating UDP socket")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except AttributeError:
            pass
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        return sock

    def start_listening(self):
        host = ''
        # host = MULTICAST_GRP
        g_ServerLog.print("[ServerUDP] Bind UDP %s:%d" % (MULTICAST_GRP, self.port))
        self.socket.bind((host, self.port))

        mreq = socket.inet_aton(MULTICAST_GRP) + socket.inet_aton(g_Host)
        # mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GRP), socket.INADDR_ANY)

        self.socket.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(g_Host))
        self.socket.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        g_ServerLog.print("[ServerUDP] listening...")

    def wait_client(self):
        connection = data, addr = self.socket.recvfrom(BUFSIZ)
        g_ServerLog.print("[ServerUDP] Received from %s:%d" % (str(addr[0]), addr[1]))
        return connection

    def create_client(self, connection):
        return ClientUDP(connection)


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
        g_HeartbeatLog.print("[Remote %d] Creating socket" % remote.Id)
        g_HeartbeatLog.print("[Remote %d] Starting heartbeat" % remote.Id)

        self.hb = RepeatedTimer(g_heartbeatInterval, self.heartbeat)

    def heartbeat(self):
        global g_heartbeatInterval

        host = socket.gethostbyname(self.remote.addr)
        g_HeartbeatLog.print(
            "[Remote %d] Sending heartbeat %s:%d"
            % (self.remote.Id, host, self.remote.port_heart()))

        sock_fd = Heartbeat.create_socket()
        sock_fd.settimeout(self.timeout())
        try:
            sock_fd.connect((host, self.remote.port_heart()))
            # send my id as heartbeat
            msg = str(g_ServerTCP.Id)
            sock_fd.send(msg.encode('ascii'))
        except ConnectionRefusedError:
            g_HeartbeatLog.print(
                "[Remote %d] Refused heartbeat" % self.remote.Id)
            pass
        finally:
            g_HeartbeatLog.print(
                "[Remote %d] Closing socket" % self.remote.Id)

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
        g_HeartbeatLog.print("[Remote %d] created" % self.Id)
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
        g_HealthMonitorLog.print("[HealthMonitor] created thread %s" % str(threading.current_thread().ident))

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
            if idx != g_ServerTCP.Id:
                # create and add Heartbeat
                heartbeat_list.append(Heartbeat(remote))

    # Thread method invoked when started
    def run(self):
        g_HealthMonitorLog.print("[HealthMonitor] Bind TCP %s:%d" % (g_Host, g_ServerTCP.port_heart()))
        # receive from any source, in 'portHG()' port
        self.socketListenHeartbeats.bind((g_Host, g_ServerTCP.port_heart()))

        g_HealthMonitorLog.print("[HealthMonitor] listening for heartbeats...")
        self.socketListenHeartbeats.listen(self.queueSize)

        while True:
            # accept connection
            conn, addr = self.socketListenHeartbeats.accept()
            g_HealthMonitorLog.print(
                '[HealthMonitor] Connected %s:%d' % (str(addr[0]), addr[1]))
            # receive heartbeat
            data = conn.recv(BUFSIZ)
            # heartbeat has the server id
            idx = data.decode('ascii')
            g_HealthMonitorLog.print("[HealthMonitor] Heartbeat from %s" % idx)
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
            g_HealthMonitorLog.print(
                "[HealthMonitor] Server %d heartbeat, delta = %dms; dev = %d"
                % (idx, timedelta_ms(timedelta), self.remotes[idx].devHB))
            # close connection
            conn.close()

    def leader(self):
        global g_heartbeatInterval
        g_HealthMonitorLog.print("[HealthMonitor] leader calc")
        # calculate tolerance
        now = datetime.datetime.now()
        # return first remote Id considered available
        for re in self.remotes:
            if re.Id == g_ServerTCP.Id:  # local
                g_HealthMonitorLog.print("[HealthMonitor] Leader is %d, me" % re.Id)
                return re.Id
            timeout = datetime.timedelta(milliseconds=int(1000 * g_heartbeatInterval + 4 * re.devHB))
            g_HealthMonitorLog.print(
                "[HealthMonitor] %d timeoutInterval = %dms"
                % (re.Id, 1000*timeout.total_seconds()))
            tolerance = now - timeout
            last = re.lastHeartbeat
            delta = timedelta_ms(last - tolerance)
            g_HealthMonitorLog.print("[HealthMonitor] %d delta = %dms" % (re.Id, delta))
            # inside tolerance
            if delta > 0:  # TODO test this
                g_HealthMonitorLog.print("[HealthMonitor] Leader is %d" % re.Id)
                return re.Id
        return -1  # should be impossible, local server delta = 0


def main(argv):
    # Create Loggers
    global g_ServerLog
    # ServerLogFile = open("log/Server.log", "w")
    # g_ServerLog = logger.Logger(ServerLogFile)
    g_ServerLog = logger.Logger(sys.stdout)
    g_ServerLog.header("Server")

    global g_HealthMonitorLog
    # HealthMonitorFile = open("log/HealthMonitor.log", "w")
    # g_HealthMonitorLog = logger.Logger(HealthMonitorFile)
    g_HealthMonitorLog = logger.Logger(sys.stdout)
    g_HealthMonitorLog.header("HealthMonitor")

    global g_HeartbeatLog
    # HeartbeatFile = open("log/Heartbeat.log", "w")
    # g_HeartbeatLog = logger.Logger(HeartbeatFile)
    g_HeartbeatLog = logger.Logger(sys.stdout)
    g_HeartbeatLog.header("Heartbeat")

    global g_Host
    # get my host
    g_Host = socket.gethostbyname(socket.getfqdn())

    # check parameters
    if len(argv) < 2:
        print("Hostname: %s" % g_Host)
        print("Usage %s [port]" % argv[0])
        sys.exit(0)
    # get parameters
    my_port = int(argv[1])

    # get remotes registered
    remote_list, server_id = remotes.create_remote_list(g_Host, my_port)
    if server_id == -1:
        print("Error: I'm not registered on servers.txt\nlocalhost is not a valid entry: use the machine name")
        sys.stdout.flush()
        sys.exit(1)

    # Start Server
    global g_ServerTCP
    g_ServerTCP = ServerTCP(server_id, my_port)
    g_ServerTCP.start()
    global g_ServerUDP
    g_ServerUDP = ServerUDP(server_id, MULTICAST_PORT)
    g_ServerUDP.start()

    # Start HealthMonitor
    global g_HealthMonitor
    g_HealthMonitor = HealthMonitor(remote_list)
    g_HealthMonitor.start()


if __name__ == "__main__":
    main(sys.argv[0:])
