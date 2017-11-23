import sys
import socket
import select
import string
import Queue
import pdb


buf_size = 1024

def main():
    client = Client()
    client.get_cmd()

class Client:
    def __init__(self):
        self.port = 8080
        self.host = 'localhost'
        self.quit = False
        self.reqs_queue = Queue.Queue()
		# Attempt to connect to server
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print('Successfully Connected to Server\n')
        except:
            print('Failed to Connect to Server\n')
         
    def enqueue_reqs(self, reqs):
        self.reqs_queue.put(reqs)
        
    def dequeue_reqs(self):
        try :
            return self.reqs_queue.get()
        except Queue.Empty:
            print("Numbers of Requests don't match with responses\n")
        
                
    def get_cmd(self):
        while not self.quit:
            try:
                readable, writable, errored = select.select([0, self.socket], [],[])
                for conn in readable:
                    if conn == 0:
                        # read user input from stdin
                        cmd = sys.stdin.readline().strip()
                        reqs = cmd.split(" ")
                        req = self.check_req(reqs)
        
                        if req is 'INVALID':
                            print("Invalid command.\n")
                        elif req is 'WRONG_ARGS':
                            print("Wrong number of arguments for \"" + reqs[0] + "\"\n")
                        elif req is 'QUIT':
                           # client mark itself as "quit"
                           # also sends request "QUIT" to server
                           self.quit = True
                           self.socket.send(cmd + '\n')
                           self.enqueue_reqs(reqs)
                           #resp = self.socket.recv(buf_size)
                           #self.parse_response(reqs, resp) 
                        elif req is 'PFILE':
                            fname = reqs[2]
                            fp = open(fname, 'rb')
                            if not fp:
                                print("File does not exist.\n")
                            else:
                                self.socket.send(cmd)
                                resp = self.socket.recv(buf_size)
                                self.parse_response(reqs, resp)
                                if resp == 'OK_PFILE':
                                    self.send_file(fp)
                                    print("\nFile transferred\n")
                            self.reqs_queue.put(reqs)
                        else:
                            # valid command, forward to server
                            self.socket.send(cmd + '\n')
                            self.reqs_queue.put(reqs)
                            
                    else:
                        # conn == self.socket
                        # got message from one room from server, display it directly
                        msg = self.socket.recv(buf_size)
                        # if there is no connection to server, quit 
                        if not msg:
                            sys.exit("Lost connection to server.\n")
                            
                        #self.parse_server_msg(msg);
                        self.parse_multi_msg(msg)
                        #print("queue: ", repr(self.reqs_queue))
            
            except KeyboardInterrupt:
                self.socket.send('QUIT\n')
                self.enqueue_reqs(['QUIT'])
                self.quit = True
                print('Keyboard Interrupt. Disconnected. \n')
                self.socket.close()
                break        
                        
    def parse_multi_msg(self, msg):
        multi_msg = msg.strip().split("\n")
        for message in multi_msg:
            self.parse_msg(message)
    
    def parse_msg(self, msg):
        parsed = msg.strip().split(" ")
        status = parsed[0]   
        # response about register
        # type could either be MESSAGE or PING
        if status == 'PING':
            self.socket.send('PONG\n')
        elif status == 'NOTICE':
            print(' '.join(parsed[1:]) + "\n")
            sys.stdout.flush()
        elif status == 'MESSAGE':
            print("Message from " + parsed[1] + " in room " + parsed[2]+ ": " + ' '.join(parsed[3:]) + "\n")
            # MESSAGE lunch_room hello everyone mark17
            sys.stdout.flush()
        elif status == 'PMESSAGE':
            print("Message from " + parsed[1] + " user " + parsed[2] + ": " + ' '.join(parsed[3:]) + "\n")
            sys.stdout.flush()

        elif status =='PFILE':
            fname = parsed[3]
            print("Receiving file from " + parsed[1] + " user " + parsed[2] + ": " + fname + " ...")
            self.receive_file(fname)
            print("File received.\n")
            
        elif status == 'OK_REG':
            reqs = self.dequeue_reqs()
            print("Registered successfully.\n")
        elif status == 'ERR_USERNAME_TAKEN':
            reqs = self.dequeue_reqs()
            print("Name taken.\n") 
        elif status == 'ERR_USER_NOT_EXIST':
            # this resp can come from many requests when the client tries to create/join/leave/message
            # before register
            reqs = self.dequeue_reqs()
            print("You need to register first.\n")
        # response about creating a new room 
        elif status == 'OK_CREATE_ROOM':
            reqs = self.dequeue_reqs()
            print("Room " + reqs[1] + " created.\n")
        elif status == 'ERR_ALREADY_IN_ROOM':
            reqs = self.dequeue_reqs()
            print("You are already in room " + reqs[1] + ".\n")

        elif status == 'ERR_ROOM_NAME_TAKEN':
            reqs = self.dequeue_reqs()
            print("Room name " + reqs[1] + " is taken.\n")
                            
        # response about joining a room
        elif status == 'OK_JOIN_ROOM':
            reqs = self.dequeue_reqs()
            print("Joined room " + reqs[1] + ".\n")

        elif status == 'ERR_ALREADY_IN_ROOM':
            reqs = self.dequeue_reqs()
            print("You are already in room " + reqs[1] + ".\n")

        elif status == 'ERR_ROOM_NOT_EXIST':
            reqs = self.dequeue_reqs()
            print("There is no room named " + reqs[1] + ".\n")

        # response about leaving a room
        elif status == 'OK_LEAVE_ROOM':
            reqs = self.dequeue_reqs()
            print("Left room " + reqs[1] + ".\n")

        elif status == 'ERR_NOT_IN_ROOM':
            reqs = self.dequeue_reqs()
            # also used as response to MESSAGE when the user is not in the room they are sending message to
            print("You are not in room " + reqs[1] + ".\n")
                                                       
        elif status == 'ERR_ROOM_NOT_EXIST':
            reqs = self.dequeue_reqs()
            print("There is no room named " + reqs[1] + ".\n")

              
        # response about listing rooms
        elif status == 'OK_LIST':
            reqs = self.dequeue_reqs()
            if len(parsed) == 1:
                print("No Available Rooms.\n")  
            else:
                print("Available Rooms: " + ' '.join(parsed[1:]) + ".\n")
              
        # response about listing members of a room
        elif status == 'OK_MEMBERS':
            reqs = self.dequeue_reqs()
            if len(parsed) == 1:
                print("This room is empty.\n")  
            else:
                print("Members in room " + reqs[1] + ": " + ' '.join(parsed[1:])  + ".\n")

   
        # response about sending a message
        elif status == 'OK_MESSAGE':
            reqs = self.dequeue_reqs()
            print("Message sent to room " + reqs[1] + ".\n")                        
            
        # response about sending a private message
        elif status == 'OK_PMESSAGE':
            reqs = self.dequeue_reqs()
            print("Message sent to user " + reqs[1] + ".\n")

        elif status == 'ERR_PUSER_NOT_EXIST':
            reqs = self.dequeue_reqs()
            print("User " + reqs[1] + " does not exist.\n") 

        # response about quit
        elif status == 'OK_QUIT':
            reqs = self.dequeue_reqs()
            print("Disconnected.\n")
        elif status == 'ERR_QUIT':
            reqs = self.dequeue_reqs()
            print("...\n")
        elif status == 'OK_PFILE':
            reqs = self.dequeue_reqs()
            print("Sending file ...")
        else:
            print("Unparsed message from server:\n " + msg + "\n") 
                        
            
    def check_req(self, reqs):
        # check if the request is valid
        valid_cmds = ['REGISTER', 'JOIN', 'LEAVE', 'MESSAGE', 'PMESSAGE','QUIT', 'LIST', 'CREATE', 'LIST_MY_ROOMS', 'MEMBERS', 'PFILE']
        # return the request type of the cmd
        if reqs[0] not in valid_cmds:
            return 'INVALID'
        elif ((reqs[0] == 'QUIT' or reqs[0] == 'LIST' or reqs[0] == 'LIST_MY_ROOMS') and len(reqs) != 1):
            return 'WRONG_ARGS'
        elif ((reqs[0] == 'REGISTER' or reqs[0] == 'JOIN' or reqs[0] == 'CREATE' or reqs[0] == 'MEMBERS' or reqs[0] == 'LEAVE') and len(reqs) != 2 ):  
            return "WRONG_ARGS"
        elif ((reqs[0] == 'MESSAGE' or reqs[0] == 'PMESSAGE' or reqs[0] == 'PFILE') and len(reqs) < 3):
            # at least 3 args. Can be more than 3 because spaces are allowed in message body
            return "WRONG_ARGS"        
        else:
            return reqs[0]
        
    def send_file(self, fp):
        # read and send the file content
        batch = fp.read(buf_size)
        while batch:
            self.socket.send(batch)
            batch = fp.read(buf_size)
        fp.close()
        
    def receive_file(self, fname):
        with open(fname, 'wb') as fp:
            # open a file with the specified name
            while True:
                data = self.socket.recv(buf_size)
                if not data:
                    break
                fp.write(data)
        fp.close()
        
if __name__ == '__main__':
    main()

