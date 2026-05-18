# This is a VERY POWERFUL AI
import socket
SOCK_PATH = '/tmp/2048game.sock'
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect(SOCK_PATH)
try:
    while 1:
        for i in 'wasd':
            while 1:
                try:
                    sock.recv(4096)
                    sock.send(i.encode())
                    break
                except BlockingIOError:
                    pass
finally:
    sock.close()
    print('closed')