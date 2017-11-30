import sys
import socket
import select
import string
import Queue
from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Cipher import PKCS1_OAEP
import ast


buf_size = 1024

def main():
    client = Client()
    client.get_cmd()
    
class Pcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
def print_ok(msg):
    print(Pcolors.OKGREEN + msg + Pcolors.ENDC)
def print_err(msg):
    print(Pcolors.FAIL + msg + Pcolors.ENDC)
def print_notice(msg):
    print(Pcolors.OKBLUE + msg + Pcolors.ENDC)

class Client:
    def __init__(self):
        self.port = 8080
        self.host = 'localhost'
        self.quit = False
        self.reqs_queue = Queue.Queue()
        self.keys = None
        self.public_key = None
        self.server_public_key = None
        self.gen_keys()
		# Attempt to connect to server
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print('Successfully Connected to Server\n')

            
        except:
            sys.exit('Failed to Connect to Server\n')
         
    def enqueue_reqs(self, reqs):
        self.reqs_queue.put(reqs)
        
    def dequeue_reqs(self):
        try :
            return self.reqs_queue.get()
        except Queue.Empty:
            print("Numbers of Requests don't match with responses\n")
    def gen_keys(self):
        #Generate private and public keys
        random_generator = Random.new().read
        self.keys = RSA.generate(1024, random_generator)
        self.public_key = self.keys.publickey() 
        
    def encrypt_msg(self, msg):
        # if server_public_key is None, the user hasn't registered yet
        # encrypt it with client's public key so that it is encrypted.
        # server will reject the message anyway.
        if not self.server_public_key:
            self.server_public_key = self.public_key 
        encryptor = PKCS1_OAEP.new(self.server_public_key)
        encrypted = encryptor.encrypt(msg)
        print("encrypted: ", encrypted)
        return encrypted
        
    def decrypt_msg(self, encrypted):
        decryptor =PKCS1_OAEP.new(self.keys)
        decrypted = decryptor.decrypt(encrypted)
        print("decrypted: ", decrypted)
        return decrypted   
    
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
                        #print("cmd", cmd)
                        #print("reqs", reqs)
                        #print("req", req)
        
                        if req == 'INVALID':
                            print_err("Invalid command.\n")
                        elif req == 'WRONG_ARGS':
                            print_err("Wrong number of arguments for \"" + reqs[0] + "\"\n")
                        elif req == 'MESSAGE':
                            msg = ' '.join(reqs[2:])
                            print("msg", msg)
                            encrypted_msg = self.encrypt_msg(msg)
                            ncmd = 'MESSAGE ' + reqs[1] + ' ' + encrypted_msg
                            self.socket.send(ncmd + '\n\n\n')
                            self.reqs_queue.put(reqs)
                        elif req == 'PMESSAGE':
                            msg = ' '.join(reqs[2:])
                            print("msg", msg)
                            encrypted_msg = self.encrypt_msg(msg)
                            ncmd = 'PMESSAGE ' + reqs[1] + ' ' + encrypted_msg
                            self.socket.send(ncmd + '\n\n\n')
                            self.reqs_queue.put(reqs)
                        elif req == 'QUIT':
                           # client mark itself as "quit"
                           # also sends request "QUIT" to server
                           self.quit = True
                           self.socket.send(cmd + '\n\n\n')
                           self.enqueue_reqs(reqs)
                           #resp = self.socket.recv(buf_size)
                           #self.parse_response(reqs, resp) 
                        else:
                            # valid command, forward to server
                            self.socket.send(cmd + '\n\n\n')
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
                self.socket.send('QUIT\n\n\n')
                self.enqueue_reqs(['QUIT'])
                self.quit = True
                print('Keyboard Interrupt. Disconnected. \n')
                self.socket.close()
                break        
                        
    def parse_multi_msg(self, msg):
        multi_msg = msg.strip().split("\n\n\n")
        for message in multi_msg:
            self.parse_msg(message)
    
    def parse_msg(self, msg):
        parsed = msg.strip().split(" ")        
        status = parsed[0] 
        # Message from server
        if status == 'PUBLIC_KEY':
            key_str = ' '.join(parsed[1:])
            self.server_public_key = RSA.importKey(key_str)
        elif status == 'SERVER_DISCONNECT':
            sys.exit("Server disconnected.\n")
        elif status == 'PING':
            self.socket.send('PONG\n\n\n')
        elif status == 'NOTICE':
            print_notice(' '.join(parsed[1:]) + "\n")
            sys.stdout.flush()
        elif status == 'MESSAGE':
            msg = ' '.join(parsed[3:]) 
            decrypted_msg = self.decrypt_msg(msg)
            print_notice("Message from " + parsed[1] + " in room " + parsed[2]+ ": " + decrypted_msg + "\n")
            # MESSAGE lunch_room hello everyone mark17
            sys.stdout.flush()
        elif status == 'PMESSAGE':
            msg = ' '.join(parsed[2:]) 
            decrypted_msg = self.decrypt_msg(msg)
            print_notice("Private message from " + parsed[1] + ": " + decrypted_msg + "\n")
            sys.stdout.flush() 
            # response about register
        elif status == 'OK_REG':
            reqs = self.dequeue_reqs()
            print_ok("Registered successfully.\n")
            
            # send public_key to server
            self.socket.send('PUBLIC_KEY ' + self.public_key.exportKey('DER') + '\n\n\n')
            
        elif status == 'ERR_USERNAME_TAKEN':
            reqs = self.dequeue_reqs()
            print_err("The name has been taken.\n") 
        
        elif status == 'ERR_ALREADY_REGISTERED':
            reqs = self.dequeue_reqs()
            print_err("You have already registered.\n")   
            
        elif status == 'ERR_USER_NOT_EXIST':
            # this resp can come from many requests when the client tries to create/join/leave/message
            # before register
            reqs = self.dequeue_reqs()
            print_err("You need to register first.\n")
        # response about creating a new room 
        elif status == 'OK_CREATE_ROOM':
            reqs = self.dequeue_reqs()
            print_ok("Room " + reqs[1] + " created.\n")
        elif status == 'ERR_ALREADY_IN_ROOM':
            reqs = self.dequeue_reqs()
            print_err("You are already in room " + reqs[1] + ".\n")

        elif status == 'ERR_ROOM_NAME_TAKEN':
            reqs = self.dequeue_reqs()
            print_err("Room name " + reqs[1] + " is taken.\n")
                            
        # response about joining a room
        elif status == 'OK_JOIN_ROOM':
            reqs = self.dequeue_reqs()
            print_ok("Joined room " + reqs[1] + ".\n")

        elif status == 'ERR_ALREADY_IN_ROOM':
            reqs = self.dequeue_reqs()
            print_err("You are already in room " + reqs[1] + ".\n")

        elif status == 'ERR_ROOM_NOT_EXIST':
            reqs = self.dequeue_reqs()
            print_err("There is no room named " + reqs[1] + ".\n")

        # response about leaving a room
        elif status == 'OK_LEAVE_ROOM':
            reqs = self.dequeue_reqs()
            print_ok("Left room " + reqs[1] + ".\n")

        elif status == 'ERR_NOT_IN_ROOM':
            reqs = self.dequeue_reqs()
            # also used as response to MESSAGE when the user is not in the room they are sending message to
            print_err("You are not in room " + reqs[1] + ".\n")
                                                       
        elif status == 'ERR_ROOM_NOT_EXIST':
            reqs = self.dequeue_reqs()
            print_err("There is no room named " + reqs[1] + ".\n")

              
        # response about listing rooms
        elif status == 'OK_LIST':
            reqs = self.dequeue_reqs()
            if len(parsed) == 1:
                print_ok("No Available Rooms.\n")  
            else:
                print_ok("Available Rooms: " + ' '.join(parsed[1:]) + ".\n")
              
        # response about listing members of a room
        elif status == 'OK_MEMBERS':
            reqs = self.dequeue_reqs()
            if len(parsed) == 1:
                print_ok("This room is empty.\n")  
            else:
                print_ok("Members in room " + reqs[1] + ": " + ' '.join(parsed[1:])  + ".\n")

   
        # response about sending a message
        elif status == 'OK_MESSAGE':
            reqs = self.dequeue_reqs()
            print_ok("Message sent to room " + reqs[1] + ".\n")                        
            
        # response about sending a private message
        elif status == 'OK_PMESSAGE':
            reqs = self.dequeue_reqs()
            print_ok("Private message sent to user " + reqs[1] + ".\n")

        elif status == 'ERR_RECVR_NOT_EXIST':
            reqs = self.dequeue_reqs()
            print_err("User " + reqs[1] + " does not exist.\n") 

        # response about quit
        elif status == 'OK_QUIT':
            reqs = self.dequeue_reqs()
            print_ok("Disconnected.\n")
        elif status == 'ERR_QUIT':
            reqs = self.dequeue_reqs()
            print_err("Can't quit now\n")
        else:
            print("Unparsed message from server:\n" + msg + "\n") 
                        
            
    def check_req(self, reqs):
        # check if the request is valid
        valid_cmds = ['REGISTER', 'JOIN', 'LEAVE', 'MESSAGE', 'PMESSAGE','QUIT', 'LIST', 'CREATE', 'LIST_MY_ROOMS', 'MEMBERS']
        # return the request type of the cmd
        if reqs[0] not in valid_cmds:
            return 'INVALID'
        elif ((reqs[0] == 'QUIT' or reqs[0] == 'LIST' or reqs[0] == 'LIST_MY_ROOMS') and len(reqs) != 1):
            return 'WRONG_ARGS'
        elif ((reqs[0] == 'REGISTER' or reqs[0] == 'JOIN' or reqs[0] == 'CREATE' or reqs[0] == 'MEMBERS' or reqs[0] == 'LEAVE') and len(reqs) != 2 ):  
            return "WRONG_ARGS"
        elif ((reqs[0] == 'MESSAGE' or reqs[0] == 'PMESSAGE') and len(reqs) < 3):
            # at least 3 args. Can be more than 3 because spaces are allowed in message body
            return "WRONG_ARGS"        
        else:
            return reqs[0]
        
        
if __name__ == '__main__':
    main()

