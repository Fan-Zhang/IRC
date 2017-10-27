import select
import socket
import sys


def main():
    host = ''
    port = 8080
    backlog = 5
    size = 1024
    users = set()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print 'Server is now running on port 8080'
    server.bind((host,port))
    server.listen(5)
    inputs = [server]
    running = 1
    while running:
        readable, writable, exceptional = select.select(inputs,[],[])
        for s in readable:
            if s is server:
                # handle the server socket
                conn, addr = server.accept()
                print 'client is at', addr
                inputs.append(conn)
                conn.send('Please provide a user name: \n')
                data = conn.recv(size)
                while data in users:
                    conn.send('Name used\n')
                    data = conn.recv(size)
                #print users
                users.add(data)
                #print users
                conn.send('Hello ' + data + '\n')


    server.close()

if __name__ == '__main__':
    main()
