import sys
import socket
import select
import string

buf_size = 1024

def main():
    client = Client()
    client.getCmd()

class Client:
    def __init__(self):
        self.port = 8080
        self.host = 'localhost'
        self.quit = False
		# Attempt to connect to server
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            sys.stdout.write('Successfully Connected to Server\n')
        except:
            sys.stdout.write('Failed to Connect to Server')
            
    def getCmd(self):
        while not self.quit:
            readable, writable, errored = select.select([0, self.socket], [],[])
            for conn in readable:
                if conn == 0:
                    # read user input from stdin
                    cmd = sys.stdin.readline().strip()
                    req = self.parseCmd(cmd)
                
                    if req is 'INVALID':
                        sys.stdout.write("Invalid command.\n")
                    elif req is 'QUIT':
                       # disconnect client
                       self.quit = True
                    else:
                        # valid command, forward to server
                        self.socket.send(cmd)
                        # receive and parse the response from server
                        resp = self.socket.recv(buf_size)
                        if resp == 'OK_REG':
                            sys.stdout.write("Registered successfully.\n")                    
                        else:
                            sys.stdout.write("Name taken.\n")                    
                
                else:
                    # conn == self.socket
                    # got message from server
                    resp = self.socket.recv(buf_size)
                    sys.stdout.write(resp)

                
    def parseCmd(self, cmd):
        
        valid_cmds = ['REGISTER', 'JOIN', 'LEAVE', 'MESSAGE', 'QUIT', 'LIST_ROOMS', 'CREATE_ROOM', 'LIST_MY_ROOMS']
        # return the request type of the cmd
        req = cmd.split(" ")[0]
        if req in valid_cmds:
            return req;
        else:
            return 'INVALID'
            

if __name__ == '__main__':
    main()

