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
                    reqs = cmd.split(" ")
                    
                    req = reqs[0]
    
                    if req is 'INVALID':
                        sys.stdout.write("Invalid command.\n")
                    elif req is 'QUIT':
                       # client mark itself as "quit"
                       # also sends request "QUIT" to server
                       self.quit = True
                       self.socket.send(cmd)
                       resp = self.socket.recv(buf_size)
                       if resp == 'OK_QUIT':
                           sys.stdout.write("Disconnected.\n")                    
                       else:
                           sys.stdout.write("...\n")  
                    else:
                        # valid command, forward to server
                        self.socket.send(cmd)
                        # receive and parse the response from server
                        resp = self.socket.recv(buf_size)
                        
                        self.printResponse(reqs, resp);
                else:
                    # conn == self.socket
                    # got message from server, display it directly
                    resp = self.socket.recv(buf_size)
                    sys.stdout.write(resp)
            
                    
    def printResponse(self, reqs, resp):
        parsed = resp.split(" ")
        status = parsed[0]     
        # response about register
        if status == 'OK_REG':
            sys.stdout.write("Registered successfully.\n")                    
        elif status == 'ERR_USER_NAME_TAKEN':
            sys.stdout.write("Name taken.\n")  
        elif status == 'ERR_USER_NOT_EXIST':
            # this resp can come from many requests when the client tries to create/join/leave/message
            # before register
            sys.stdout.write("You need to register first.\n")       
        # response about creating a new room 
        elif status == 'OK_CREATE_ROOM':
            sys.stdout.write("Room " + reqs[1] + " created.\n") 
        elif status == 'ERR_ALREADY_IN_ROOM':
            sys.stdout.write("You are already in room " + reqs[1] + ".\n") 
        elif status == 'ERR_ROOM_NAME_TAKEN':
            sys.stdout.write("Room name " + reqs[1] + " is taken.\n")  
                            
        # response about joining a room
        elif status == 'OK_JOIN_ROOM':
            sys.stdout.write("Joined room " + reqs[1] + ".\n") 
        elif status == 'ERR_ALREADY_IN_ROOM':
            sys.stdout.write("You are already in room " + reqs[1] + ".\n") 
        elif status == 'ERR_ROOM_NOT_EXIST':
            sys.stdout.write("There is no room named " + reqs[1] + ".\n") 
                         
        # response about leaving a room
        elif status == 'OK_LEAVE_ROOM':
            sys.stdout.write("Left room " + reqs[1] + ".\n") 
        elif status == 'ERR_NOT_IN_ROOM':
            sys.stdout.write("You are not in room " + reqs[1] + ".\n")                                                          
        elif status == 'ERR_ROOM_NOT_EXIST':
            sys.stdout.write("There is no room named " + reqs[1] + ".\n")  
              
              
        # response about listing rooms
        elif status == 'OK_LIST':
            if len(parsed) == 1:
                sys.stdout.write("No Available Rooms.\n")  
            else:
                sys.stdout.write("Available Rooms: " + ' '.join(parsed[1:]) + ".\n")  
    
        # response about sending a message
        elif status == 'OK_MSG':
            sys.stdout.write("Message sent to room " + reqs[1] + ".\n")            
        elif status == 'ERR_MSG':
            sys.stdout.write("Message failed to be sent to room " + reqs[1] + ".\n")
        else:
            sys.stdout.write("Message from server: \n" + resp + "\n")
            
    
    def checkReq(self, req):
        # check if the request is valid
        valid_cmds = ['REGISTER', 'JOIN', 'LEAVE', 'MESSAGE', 'QUIT', 'LIST', 'CREATE', 'LIST_MY_ROOMS']
        # return the request type of the cmd
        if req in valid_cmds:
            return req;
        else:
            return 'INVALID'            

if __name__ == '__main__':
    main()

