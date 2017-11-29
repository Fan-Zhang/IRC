import select
import socket
import sys
from threading import Thread
from time import sleep

from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Cipher import PKCS1_OAEP
import ast


# TODO:
# 2. QUIT (optional)
# 3. notice room members when a client has left (optional)
# 4. notice room members when new member joins (optional)
# 5. dictionary changed size during iteration: when new user or user leave room
#    save dict in a local variable and check if user is active before sending
# 8. add `try` `except` to handle keyboard interrupt
# 9. check not only user name but also socket when new user
#10. read `QUIT` from stdin to disconnect from clients



# global variable
my_server = None


# main function
def main():
    global my_server
    my_server = Server()
    my_server.start()
    my_server.generate_RSA_keys()
    my_server.send_keepalive_messages()
    my_server.accept_requests()



#####################################################
# User Class

class User:
    def __init__(self, name, socket):
        self.name = name
        self.socket = socket
        self.active = True  # the user is connected
        self.public_key = None

    def get_name(self):
        return self.name

    def get_rooms(self):
        rms = []
        for room in my_server.get_rooms().itervalues():
            if self.name in room.get_members():
                rms.append(room.get_name())
        return rms

    def get_socket(self):
        return self.socket

    # mark the user as active
    def mark_active(self):
        self.active = True
    
    # mark the user as inactive
    def mark_inactive(self):
        self.active = False
    
    # check if the user is active
    def is_active(self):
        return self.active

# User Class - end
#####################################################


#####################################################
# Room Class

class Room:
    def __init__(self, name):
        self.name = name
        self.members = set() # a set of sockets

    def get_name(self):
        return self.name

    def add_member(self, socket):
        if socket in self.members:
            return "ERR_ALREADY_IN_ROOM"
        #user = get_server_instance().find_user(socket)
        user = my_server.find_user(socket)
        if not user:
            return "ERR_USER_NOT_EXIST"

        self.members.add(socket)
        return "OK_JOIN_ROOM"

    def remove_member(self, socket):
        if socket not in self.members:
            return "ERR_NOT_IN_ROOM"
        user = my_server.find_user(socket)
        if not user:
            return "ERR_USER_NOT_EXIST"

        self.members.remove(socket)
        return "OK_LEAVE_ROOM"

    def get_members(self):
        members = []
        for socket in self.members:
            #user = get_server_instance().find_user(socket)
            user = my_server.find_user(socket)
            if user:
                members.append(user.get_name())

        return members

    def get_member_sockets(self):
        return self.members

# Room Class - end
#####################################################

#####################################################
# Server Class

class Server:
    def __init__(self):
            self.host = ''
            self.port = 8080
            self.backlog = 5
            self.size = 1024
            self.running = True
            self.inputs = [0]
            self.users = {}  # a dictionary:  key - user name; value - user object
            self.rooms = {}  # a dictionary:  key - room name; value - room object
            self.keys = None
            self.public_key = None

    def get_users(self):
        return self.users

    def get_rooms(self):
        return self.rooms

    def start(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setblocking(0)
            self.server.bind((self.host, self.port))
            self.server.listen(self.backlog)
            print "Server is running on port 8080"
        except:
            print "Failed to start the server"
        else:
            self.inputs.append(self.server)

    def generate_RSA_keys(self):
        random_generator = Random.new().read
        try:
            self.keys = RSA.generate(1024, random_generator)
            self.public_key = self.keys.publickey()
        except:
            print "Failed to generate RSA keys"


    def send_keepalive_messages(self):
        thread = Thread(target = self._ping_clients, args = (1, ))
        thread.start()


    def accept_requests(self):
        while self.running:
            readable, writable, exceptional = select.select(self.inputs,[],[])
            for s in readable:
                # read user input from stdin
                if s == 0:
                    cmd = sys.stdin.readline().strip()
                    print cmd
                # if the socket is server socket
                # accept new client connection and add it to the connection list
                elif s is self.server:
                    connection, client_address = s.accept()
                    connection.setblocking(0)
                    self.inputs.append(connection)

                # if the socket is client socket
                # read data from the socket and process them
                else:
                    data = s.recv(self.size)
                    if data:
                        responses = self._dispatch_multi(data, s)
                        #print 'responses:', responses

                        for response in responses:
                            resp = response.split(' ')
                            #print 'resp:', resp
                            status = resp[0]
                            # TODO: extract to a function
                            if status == "OK_MESSAGE":
                                s.send(status + "\n\n\n")
                                                            
                                #to_send = ' '.join(resp[1:])
                                sender = resp[1]
                                room = resp[2]
                                decrypted_msg = ' '.join(resp[3:])
                                
                                
                                print 'data:', data
                                for sckt in self.rooms[room].get_member_sockets():
                                    # encrypt message using each receiver's public key
                                    user = self.find_user(sckt)
                                    encrypted_msg = self._encrypt_msg(user, decrypted_msg)
                                    # send the encrypted message
                                    sckt.send('MESSAGE ' + sender + ' ' + room + ' ' + encrypted_msg + '\n\n\n')
                                    
                            elif status == "OK_PMESSAGE":
                                s.send(status + "\n\n\n")

                                receiver = resp[2]
                                sckt = self.users[receiver].get_socket()
                                to_send = ' '.join(resp[1:])
                                sckt.send("PMESSAGE " + to_send + '\n\n\n')
                                
                            # if the client intentionally disconnect from server
                            elif status == "OK_QUIT":
                                s.send(status + "\n\n\n")
                                self._handle_client_leave(self.find_user(s))
                                self.inputs.remove(s)
                            else:
                                s.send(response + "\n\n\n")
                    # if the socket is broken
                    else:
                        self._handle_client_leave(self.find_user(s))
                        self.inputs.remove(s)
            # end of for loop

        self.server.close()
        # end of while loop

    def find_user(self, socket):
        for user in self.users.itervalues():
            if user.get_socket() == socket:
                return user
        return None

    # data could be multiple messages queueing in the buffer, deliminated by '\n\n\n'
    # Split these messages and store them in a list, dispatch each of them,
    # store the return values in another list and return the list.
    def _dispatch_multi(self, data, socket):
        ret = []
        multi_data = data.strip().split("\n\n\n")
        #print 'multi_data:', multi_data
        for dt in multi_data:
            resp = self._dispatch(dt, socket)
            if resp:
                ret.append(resp)
        return ret
                
            
    def _dispatch(self, data, socket):
        args = data.strip().split(" ")
        cmd = args[0]
        if len(args) > 1:
            param = args[1]

        if cmd == "PUBLIC_KEY":
            # server sends its own public_key to the client, when receving client's public_key
            key_str = ' '.join(args[1:])
            self._send_public_key(key_str, socket)
        elif cmd == "REGISTER":
            user_name = param
            return self._register_user(user_name, socket)
        elif cmd == "CREATE":
            room_name = param
            return self._create_room(room_name, socket)
        elif cmd == "JOIN":
            room_name = param
            return self._join_room(room_name, socket)
        elif cmd == "LEAVE":
            room_name = param
            return self._leave_room(room_name, socket)
        elif cmd == "LIST":
            return self._list_rooms()
        elif cmd == "MEMBERS":
            room_name = param
            return self._list_members(room_name)
        elif cmd == "MESSAGE":
            room_name = param
            #msg_lst = args[2:]
            msg = ' '.join(args[2:])
            return self._send_message(room_name, socket, msg)
        elif cmd == "PMESSAGE":
            receiver = param
            msg_lst = args[2:]
            return self._send_private_message(receiver, socket, msg_lst)
        elif cmd == "QUIT":
            return self._quit(socket)
        elif cmd == "PONG":
            # if receive a 'PONG' from some user, mark it as active
            user = self.find_user(socket)
            user.mark_active()
            pass
        else:
            return "ERR_INVALID"
        
    def _ping_clients(self, seconds):
        while True:
            # iterate all clients and send 'PING' to everyone.
            # TODO: dictionary changed size during iteration
            for user in self.users.itervalues():
                sckt = user.get_socket()
                sckt.send('PING\n\n\n')

            # give client 1 second to respond, if no response in 1 sec, consider the client as crashed
            sleep(2)
            for user in self.users.itervalues():
                # if no 'PONG' was received, the client crashes, marked as inactive
                if not user.is_active():
                    # handle client crash
                    self._handle_client_leave(user)               
                # mark all the users as inactive for next round of PING
                user.mark_inactive()

            sleep(seconds)

    # called when a client sends "QUIT" or crashes
    def _handle_client_leave(self, user):
        if user:
            sckt = user.get_socket()
            sckt.close()
            
            name = user.get_name()
            rms = user.get_rooms()
            if rms:
                for rm in rms:
                    room = self.rooms[rm]
                    # remove the client from this room
                    room.remove_member(sckt)

                    # send message to other members of this room
                    sckts = room.get_member_sockets()
                    for s in sckts:
                        print 'NOTICE: user ' + name + ' has left\n'
                        s.send('NOTICE user ' + name + ' has left\n\n\n')

            # remove client from user list
            del self.users[name]

       

    def _register_user(self, name, socket):
        if name in self.users:
            return "ERR_USERNAME_TAKEN"

        new_user = User(name, socket)
        self.users[name] = new_user
        return "OK_REG"

    def _create_room(self, room, socket):
        if room in self.rooms:
            return "ERR_ROOM_NAME_TAKEN"

        new_room = Room(room) 
        self.rooms[room] = new_room
        print "Created room: ", room
        return new_room.add_member(socket)

    def _join_room(self, room, socket):
        if room not in self.rooms:
            return "ERR_ROOM_NOT_EXIST"

        rm = self.rooms[room]
        print self.find_user(socket).get_name(), "joined room", room
        return rm.add_member(socket)

    def _leave_room(self, room, socket):
        if room not in self.rooms:
            return "ERR_ROOM_NOT_EXIST"

        rm = self.rooms[room]
        print self.find_user(socket).get_name(), "left room", room
        return rm.remove_member(socket)

    def _list_rooms(self):
        rms = ' '.join(self.rooms.keys())
        print "OK_LIST ", rms
        return ("OK_LIST " + rms)

    def _list_members(self, room):
        if room not in self.rooms:
            return "ERR_ROOM_NOT_EXIST"

        rm = self.rooms[room]
        members = rm.get_members()
        print "OK_MEMBERS ", ' '.join(members)
        return ("OK_MEMBERS " + ' '.join(members))
     
    def _send_message(self, room, socket, msg):
        if room not in self.rooms:
            return "ERR_ROOM_NOT_EXIST"

        user = self.find_user(socket)
        if user:
            user_name = user.get_name()
            rm = self.rooms[room]
            # decrypt the message using sender's public_key
            
            decrypted_msg = self._decrypt_msg(msg)
            if user_name in rm.get_members():
                return ("OK_MESSAGE " + user_name + ' ' + room + ' ' + decrypted_msg)
                # the msg content is needed in the return value for server to send to other users in the room
            else:
                return "ERR_NOT_IN_ROOM"
        else:
            return "ERR_USER_NOT_EXIST"

    def _send_private_message(self, receiver, socket, msg_lst):
        user = self.find_user(socket)
        if not user:
            return "ERR_USER_NOT_EXIST"

        user_name = user.get_name()
        if receiver in self.users:
            return ("OK_PMESSAGE " + user_name + ' ' + receiver + ' ' + ' '.join(msg_lst))
        else:
            return "ERR_RECVR_NOT_EXIST"

    def _quit(self, socket):
        return "OK_QUIT"

    #  send server public key to client after receiving that of the client
    def _send_public_key(self, key_str, socket):
        user = self.find_user(socket)
        user.public_key = RSA.importKey(key_str)
        # send public_key to client
        socket.send('PUBLIC_KEY ' + self.public_key.exportKey('DER') + '\n\n\n')
        

    def _encrypt_msg(self, user, msg):  
        print("msg: ", msg)
        encryptor = PKCS1_OAEP.new(user.public_key)
        encrypted = encryptor.encrypt(msg)
        print("encrypted: ", encrypted)
        return encrypted
            
    def _decrypt_msg(self, encrypted):
        print("encrypted: ", encrypted)
        decryptor =PKCS1_OAEP.new(self.keys)
        decrypted = decryptor.decrypt(encrypted)
        print("decrypted: ", decrypted)
        return decrypted

# Server Class - end
#####################################################


if __name__ == '__main__':
    main()

