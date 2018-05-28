#!python
import socket

# create socket
sock = socket.socket(
    socket.AF_INET, socket.SOCK_STREAM)
# get local name
host = socket.gethostname()
# connect to host on the port.
port = 14699
sock.connect((host, port))
# Receive
msgBytesMax = 1024
msg = sock.recv(msgBytesMax)
# end connection
sock.close()
print(msg.decode('ascii'))
