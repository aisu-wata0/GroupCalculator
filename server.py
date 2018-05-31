#!python

import socket
import threading
from threading import Timer
import sys
import datetime
import parse
from abc import abstractmethod
# import struct

import remotes
import logger

# buffer size
BUFSIZ = 8192
g_heartbeatInterval = 4

g_ServerTCP = None
g_ServerUDP = None
g_HealthMonitorTCP = None
g_HealthMonitorUDP = None

g_Host = ""
MULTICAST_GRP = '224.1.1.1'
MULTICAST_PORT = 5007
MULTICAST_GRP_HB = '224.1.1.2'
MULTICAST_PORT_HB = MULTICAST_PORT + 1

g_ServerLog = None
g_HealthMonitorLog = None
g_HeartbeatLog = None


def socket_listen_multicast(sock, group, port):
    host = ''  # host = group
    sock.bind((host, port))
    # setup multicast
    mreq = socket.inet_aton(group) + socket.inet_aton(g_Host)
    # mreq = struct.pack("4sl", socket.inet_aton(group), socket.INADDR_ANY)
    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(g_Host))
    sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mreq)


def create_socket_multicast():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        # SO_REUSEADDR socket option allows a socket to forcibly bind to a port in use by another socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except AttributeError:
        pass
    # setup multicast
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
    return sock


# Abstract class
# Serves a connected client, the protocol must be implemented
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
        # receive expression from client
        expression = self.receive_exp()
        # calculate result
        g_ServerLog.print("[Client %s] Calculating expression: %s"
                          % (str(self.addr), expression))
        message = ""
        try:
            result = parse.create_result(expression)
            g_ServerLog.print("[Client %s] result = %s" % (str(self.addr), result))
            print("received: " + str(expression) + " result = " + str(result))
            # set response to result
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
            # respond with the message
            self.respond(message)
            # end connection
            self.sock.close()

    # retrieves the expression from user
    @abstractmethod
    def receive_exp(self):
        pass

    # receives a message and sends it to user
    @abstractmethod
    def respond(self, msg):
        pass


# TCP implementation of the client
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


# UDP implementation of the client
class ClientUDP(Client):
    def __init__(self, connection):
        super().__init__(connection)
        # Construction parameters
        self.expression = self.sock.decode('ascii')
        # create another socket to respond
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            # SO_REUSEADDR socket option allows a socket to forcibly bind to a port in use by another socket
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


# Abstract server
# This is one server in a group, it only responds if it's the leader
# the protocol must be implemented
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

    # creates a socket for listening
    @abstractmethod
    def create_socket(self):
        pass

    # Thread method invoked when started
    def run(self):
        self.setup_listening()

        while True:
            # blocks until client connects
            connection = self.wait_client()
            if self.leader_id() == self.Id:
                client = self.create_client(connection)
                client.start()

    # setup to start listening
    @abstractmethod
    def setup_listening(self):
        pass

    # Blocks until a client connects
    # returns a connection (which is dependant on the protocol implementation )
    @abstractmethod
    def wait_client(self):
        pass

    # returns the group leader id
    @abstractmethod
    def leader_id(self):
        pass

    # returns a Client thread
    @abstractmethod
    def create_client(self, connection):
        pass

    # heartbeat port
    def port_heart(self):
        return self.port + 1


# TCP implementation of Server
class ServerTCP(Server):
    def create_socket(self):
        g_ServerLog.print("[ServerTCP] Creating TCP socket")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # SO_REUSEADDR socket option allows a socket to forcibly bind to a port in use by another socket
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except AttributeError:
            pass
        return sock

    # setup to start listening
    def setup_listening(self):
        g_ServerLog.print("[ServerTCP] Bind TCP %s:%d" % (g_Host, self.port))
        queue_size = 5
        # receive from any source
        self.socket.bind((g_Host, self.port))
        self.socket.listen(queue_size)
        g_ServerLog.print("[ServerTCP] listening...")

    # Blocks until a client connects
    # returns (sock, addr) of the connected client
    def wait_client(self):
        g_ServerLog.print("[ServerTCP] Waiting client...")
        connection = sock, addr = self.socket.accept()
        g_ServerLog.print("[ServerTCP] Connected %s:%d" % (str(addr[0]), addr[1]))
        return connection

    # returns the group leader id
    def leader_id(self):
        return g_HealthMonitorTCP.leader()

    def create_client(self, connection):
        return ClientTCP(connection)


# UDP implementation of Server
class ServerUDP(Server):
    def create_socket(self):
        g_ServerLog.print("[ServerUDP] Creating UDP socket multicast")
        sock = create_socket_multicast()
        return sock

    # setup to start listening
    def setup_listening(self):
        g_ServerLog.print("[ServerUDP] Bind UDP %s:%d" % (MULTICAST_GRP, self.port))
        socket_listen_multicast(self.socket, MULTICAST_GRP, self.port)

    # Blocks until a client connects
    # returns (data, addr) of the connected client
    def wait_client(self):
        g_ServerLog.print("[ServerUDP] Waiting client...")
        connection = data, addr = self.socket.recvfrom(BUFSIZ)
        g_ServerLog.print("[ServerUDP] Received from %s:%d" % (str(addr[0]), addr[1]))
        return connection

    # returns the group leader id
    def leader_id(self):
        return g_HealthMonitorUDP.leader()

    def create_client(self, connection):
        return ClientUDP(connection)


# calls function periodically, interval is in seconds
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
            # start timer for next run
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


# Tries to send heartbeats to the remote repeatedly
# repeats by the interval constant defined 'g_heartbeatInterval'
# Used by HealthMonitor to send heartbeats to your group
# Only used by TCP since UDP can multicast
class Heartbeater:
    def __init__(self, remote):
        self.remote = remote
        g_HeartbeatLog.print("[Remote %d] Starting heartbeat" % self.remote.Id)
        # create a repeated timer that calls self.heartbeat()
        self.hb = RepeatedTimer(g_heartbeatInterval, self.heartbeat)

    # Sends heartbeat to remote
    def heartbeat(self):
        remote_host = socket.gethostbyname(self.remote.addr)
        g_HeartbeatLog.print("[Remote %d] Sending heartbeat %s:%d"
                             % (self.remote.Id, remote_host, self.remote.port_heart()))
        sock_fd = self.create_socket()
        try:
            sock_fd.connect((remote_host, self.remote.port_heart()))
            # send my id as heartbeat
            msg = str(g_ServerTCP.Id)
            sock_fd.send(msg.encode('ascii'))
        except ConnectionRefusedError:
            g_HeartbeatLog.print("[Remote %d] Refused heartbeat" % self.remote.Id)
            pass
        except Exception as e:  # Other exception
            g_HeartbeatLog.print("[Client] Heartbeat failed, Exception: " + str(e))
        finally:
            g_HeartbeatLog.print("[Remote %d] Closing socket" % self.remote.Id)
            sock_fd.close()

    # creates a socket to send heartbeats with timeout
    def create_socket(self):
        g_HeartbeatLog.print("[Remote %d] Creating socket" % self.remote.Id)
        sock_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # SO_REUSEADDR socket option allows a socket to forcibly bind to a port in use by another socket
            sock_fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except AttributeError:
            pass
        sock_fd.settimeout(self.timeout())
        return sock_fd

    @staticmethod
    def timeout():
        return int(g_heartbeatInterval / 2)


# receives a timedelta, returns its total milliseconds
def timedelta_ms(timedelta):
    delta_ms = timedelta.total_seconds() * 1000
    delta_ms += timedelta.microseconds / 1000
    return delta_ms


# Stores information of other remotes
# such as: lastHeartbeat date, heartbeat deviation.
# calculates the timeout value to use taking the devitaion into consideration
class Remote:
    def __init__(self, addr, port, idx):
        # Address : Port
        self.addr = addr
        self.port = port
        # Remote ID
        self.Id = idx
        g_HeartbeatLog.print("[Remote %d] created" % self.Id)
        # Heartbeat deviation
        self.devHB = 0
        # Initialize lastHeartbeat as invalid, too long ago
        # only sure the server in on when first heartbeat is received
        now = datetime.datetime.now()
        self.lastHeartbeat = now - self.timeout_delta()

    # heartbeat port
    def port_heart(self):
        return self.port + 1

    def beat(self):
        # Calculate delta time since last heartbeat from this server
        prev = self.lastHeartbeat
        # update heartbeat time
        self.lastHeartbeat = datetime.datetime.now()
        timedelta = self.lastHeartbeat - prev
        # update deviation
        self.devHB = 0.75 * self.devHB\
            + 0.25 * abs(timedelta_ms(timedelta) - 1000*g_heartbeatInterval)
        g_HealthMonitorLog.print("[Remote %d] Heartbeat, delta = %dms; dev = %d"
                                 % (self.Id, timedelta_ms(timedelta), self.devHB))

    # Fair timeout value for the heartbeats to assume server dead
    # Takes the deviation calculated with heartbeats into account
    def timeout_delta(self):
        global g_heartbeatInterval
        return datetime.timedelta(
            milliseconds=int(1000 * g_heartbeatInterval + 4 * self.devHB))


# Monitors other remotes by listening heartbeats
# Also sends heartbeats to others
# Calculates group leader
class HealthMonitor(threading.Thread):
    def __init__(self, remote_list):
        threading.Thread.__init__(self)
        g_HealthMonitorLog.print("[HealthMonitor] created thread %s"
                                 % str(threading.current_thread().ident))
        # create socket to listen to heartbeats
        self.socketHB = self.create_socket_hb()
        # Construct remotes and Heartbeater list
        # Remote array, see Remote class
        self.remotes = []
        # see the concrete classes implementation of heartbeats
        self.heartbeat_setup()
        for idx, remote in enumerate(remote_list):
            # get remote info
            addr, port = remote
            # create Remote object
            remote = Remote(addr, port, idx)
            self.remotes.append(remote)  # add to list
            # If not myself, send heartbeats to it
            self.heartbeat_create(idx, remote)

    # Setup for heartbeat generation
    @abstractmethod
    def heartbeat_setup(self):
        pass

    # Creates socket to listen to heartbeats
    @abstractmethod
    def create_socket_hb(self):
        pass

    # Creates a Heartbeater if needed
    @abstractmethod
    def heartbeat_create(self, idx, remote):
        pass

    # Thread method invoked when started
    # Listen to heartbeats in a loop
    def run(self):
        self.setup_listening()
        while True:
            # Blocks until a heartbeat is received
            idx = self.receive_heartbeat()
            g_HealthMonitorLog.print("[HealthMonitor] Heartbeat from %s" % str(idx))
            # Inform Remote I heard it's heartbeat
            self.remotes[idx].beat()

    # setup to start listening
    @abstractmethod
    def setup_listening(self):
        pass

    # Blocks until a heartbeat is received
    # returns id of the server that sent the heartbeat
    @abstractmethod
    def receive_heartbeat(self):
        return -1

    def leader(self):
        g_HealthMonitorLog.print("[HealthMonitor] leader calc")
        # calculate tolerance
        now = datetime.datetime.now()
        # return first remote Id considered available
        for re in self.remotes:
            if re.Id == g_ServerTCP.Id:  # local
                g_HealthMonitorLog.print("[HealthMonitor] Leader is %d, me" % re.Id)
                return re.Id
            timeout = re.timeout_delta()
            g_HealthMonitorLog.print(
                "[HealthMonitor] Remote %d timeoutInterval = %dms"
                % (re.Id, 1000*timeout.total_seconds()))
            # calculate tolerance
            tolerance = now - timeout
            last = re.lastHeartbeat
            delta = timedelta_ms(last - tolerance)
            g_HealthMonitorLog.print("[HealthMonitor] %d delta = %dms" % (re.Id, delta))
            # If inside tolerance
            if delta > 0:  # TODO test this
                g_HealthMonitorLog.print("[HealthMonitor] Leader is %d" % re.Id)
                return re.Id
        return -1  # should be impossible, I will always find myself


# Monitors other remotes by listening heartbeats
# creates Heartbeats to inform others
# Calculates group leader
class HealthMonitorTCP(HealthMonitor):
    def __init__(self, remote_list):
        # Heartbeater sending list
        self.heartbeat_list = []

        super().__init__(remote_list)

    def create_socket_hb(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # SO_REUSEADDR socket option allows a socket to forcibly bind to a port in use by another socket
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except AttributeError:
            pass
        return sock

    # Setup for heartbeat generation
    def heartbeat_setup(self):
        pass

    # Creates a Heartbeater if needed
    def heartbeat_create(self, idx, remote):
        if idx != g_ServerTCP.Id:
            # create and add Heartbeater, see it's class
            self.heartbeat_list.append(Heartbeater(remote))

    # setup to start listening
    def setup_listening(self):
        g_HealthMonitorLog.print("[HealthMonitor] Bind TCP %s:%d" % (g_Host, g_ServerTCP.port_heart()))
        queueSize = len(self.remotes) * 2
        # receive from any source
        self.socketHB.bind((g_Host, g_ServerTCP.port_heart()))
        self.socketHB.listen(queueSize)
        g_HealthMonitorLog.print("[HealthMonitor] listening for heartbeats...")

    # Blocks until a heartbeat is received
    # returns id of the server that sent the heartbeat
    def receive_heartbeat(self):
        sock, addr = self.socketHB.accept()
        g_HealthMonitorLog.print(
            '[HealthMonitor] Connected %s:%d' % (str(addr[0]), addr[1]))
        # receive heartbeat
        data = sock.recv(BUFSIZ)
        # close connection
        sock.close()
        # heartbeat has the server id
        idx = data.decode('ascii')
        return int(idx)


# Monitors other remotes by listening heartbeats
# UDP implementation uses multicast, no need to create Heartbeaters
# multicasts your own Id to your server group
# Calculates group leader
class HealthMonitorUDP(HealthMonitor):
    def __init__(self, remote_list):
        # Heartbeater sender
        self.heartbeatRepeatedSender = None

        super().__init__(remote_list)

    def create_socket_hb(self):
        g_ServerLog.print("[HealthMonitorUDP] Creating UDP socket multicast")
        sock = create_socket_multicast()
        return sock

    # Setup for heartbeat generation
    def heartbeat_setup(self):
        g_HeartbeatLog.print("[HealthMonitorUDP] Starting heartbeat sender")
        # create a repeated timer that calls self.heartbeat()
        self.heartbeatRepeatedSender = RepeatedTimer(g_heartbeatInterval, self.heartbeat)

    # Sends heartbeat to remote
    def heartbeat(self):
        g_HeartbeatLog.print("[HealthMonitorUDP] Sending heartbeat multicast")
        # send my id as heartbeat
        msg = str(g_ServerTCP.Id)
        self.socketHB.sendto(msg.encode('ascii'), (MULTICAST_GRP_HB, MULTICAST_PORT_HB))

    # Creates a Heartbeater if needed
    def heartbeat_create(self, idx, remote):
        pass

    # setup to start listening
    def setup_listening(self):
        g_HealthMonitorLog.print("[HealthMonitorUDP] Bind UDP %s:%d"
                                 % (MULTICAST_GRP_HB, MULTICAST_PORT_HB))
        socket_listen_multicast(self.socketHB, MULTICAST_GRP_HB, MULTICAST_PORT_HB)
        g_HealthMonitorLog.print("[HealthMonitorUDP] listening for heartbeats...")

    # Blocks until a heartbeat is received
    # returns id of the server that sent the heartbeat
    def receive_heartbeat(self):
        idx = g_ServerUDP.Id
        while idx == g_ServerUDP.Id:
            data, addr = self.socketHB.recvfrom(1024)
            # heartbeat has the server id
            idx = int(data.decode('ascii'))

        return idx


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
    # HeartbeatFile = open("log/Heartbeater.log", "w")
    # g_HeartbeatLog = logger.Logger(HeartbeatFile)
    g_HeartbeatLog = logger.Logger(sys.stdout)
    g_HeartbeatLog.header("Heartbeater")

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

    if len(argv) != 3 or argv[2].lower() != "tcp":
        global g_ServerUDP
        g_ServerUDP = ServerUDP(server_id, MULTICAST_PORT)
        g_ServerUDP.start()

    # Start HealthMonitor
    global g_HealthMonitorTCP
    g_HealthMonitorTCP = HealthMonitorTCP(remote_list)
    g_HealthMonitorTCP.start()
    global g_HealthMonitorUDP
    g_HealthMonitorUDP = HealthMonitorUDP(remote_list)
    g_HealthMonitorUDP.start()


if __name__ == "__main__":
    main(sys.argv[0:])
