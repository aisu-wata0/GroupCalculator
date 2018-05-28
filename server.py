#!python
import socket

# create socket
serverSocket = socket.socket(
    socket.AF_INET, socket.SOCK_STREAM)
# get local name
host = socket.gethostname()
# bind to the port
port = 14699
serverSocket.bind((host, port))
# queue up requests
queueSize = 5
serverSocket.listen(queueSize)

while True:
    # establish connection
    clientSocket, addr = serverSocket.accept()
    print("%s connected." % str(addr))
    # send response
    msg = 'Connected to ' + host + "\r\n"
    clientSocket.send(msg.encode('ascii'))
    # end connection
    clientSocket.close()