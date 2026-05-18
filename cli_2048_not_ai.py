# This is a VERY POWERFUL AI
import socket
SOCK_PATH = '/tmp/2048game.sock'
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect(SOCK_PATH)
try:
    running = 1
    while running:
        try:
            data = sock.recv(4096).decode().splitlines()
            matrix = [line.split() for line in data[2:]]
            out = [' ' + ' '.join(f'{x:5}' for x in line).rstrip() + ' ' for line in matrix]
            print('='*len(out[0]), *out,'='*len(out[0]), '', sep='\n')
            while 1:
                x = input('input (w/a/s/d):')
                if x in list('wasd'):
                    sock.send(x.encode())
                    break
                if x=='quit':
                    running = 0
                    break
            print('\n'*8)
        except BlockingIOError:
            pass
finally:
    sock.close()
    print('Closed!')