#!python
import socket

PORT = 14699
BUFSIZ = 1024

# create socket
sock = socket.socket(
    socket.AF_INET, socket.SOCK_STREAM)
# get local name
host = socket.gethostname()
# connect to host on the port.
sock.connect((host, PORT))
# Receive
msg = sock.recv(BUFSIZ)
# end connection
sock.close()
print(msg.decode('ascii'))
