import select
import socket
import sys

# globals
users = set()

def register(user):
    if user in users:
        return "ERR_USERNAME_TAKEN"
    else:
        users.add(user)
        return "OK_REG"

    
def dispatch(data, connection):
    args = data.split(" ")
    cmd = args[0]
    if cmd == "REGISTER":
        return register(args[1])
    else:
        return "ERR_INVALID"


def main():
    host = ''
    port = 8080
    backlog = 5
    size = 1024

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print "Server is running on port 8080"
    server.bind((host,port))
    server.listen(5)
    inputs = [server]
    running = 1
    while running:
        readable, writable, exceptional = select.select(inputs,[],[])
        for s in readable:
            # if the socket is server socket
            # accept new client connection and add it to the connection list
            if s is server:
                connection, client_address = s.accept()
                inputs.append(connection)
            # if the socket is client socket
            # read data from the socket and process them
            else:
                data = s.recv(size)
                if data:
                    response = dispatch(data, s)
                    if response:
                        s.send(response)
                    # if no valid response for this request
                    # continue to the next client
                    else:
                        continue
                else:
                    inputs.remove(s)
                    s.close()


    server.close()

if __name__ == '__main__':
    main()
