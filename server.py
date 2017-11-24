import select
import socket
import sys
from threading import Thread
from time import sleep

# TODO:
# 1. REMOVE EMPTY ROOM
# 2. QUIT
# 3. Other members of the room should get noticed when a client has left
# 4. Check if the user is in the room before removing them from the room if they send "LEAVE xx".
# 5. leave() method
# 6. server not exit with keyboard interrupt
# 7. notice room members when new member joins


#####################################################
# User Class

class User:
    def __init__(self, name, socket):
        self.name = name
        self.socket = socket
        self.active = True  # the user is connected

    def get_name(self):
        return self.name

    def get_rooms(self):
        rms = []
        for room in rooms.itervalues():
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
        if self.name not in rooms:
            return "ERR_ROOM_NOT_EXIST"
        if socket in self.members:
            return "ERR_ALREADY_IN_ROOM"
        user = find_user(socket)
        if user:
            self.members.add(socket)
            return "OK_JOIN_ROOM"
        else:
            return "ERR_USER_NOT_EXIST"

    def remove_member(self, socket):
        if self.name not in rooms:
            return "ERR_ROOM_NOT_EXIST"
        if socket not in self.members:
            return "ERR_NOT_IN_ROOM"
        user = find_user(socket)
        if user:
            self.members.remove(socket)
            return "OK_LEAVE_ROOM"
        else:
            return "ERR_USER_NOT_EXIST"

    def get_members(self):
        members = []
        for socket in self.members:
            user = find_user(socket)
            if user:
                members.append(user.get_name())

        return members

    def get_member_sockets(self):
        return self.members

# Room Class - end
#####################################################

#####################################################
# globals

users = {} # a dictionary:  key - user name; value - user object
rooms = {} # a dictionary:  key - room name; value - room object

# globals - end
#####################################################


#####################################################
# dispatch functions

def register(name, socket):
    if name in users:
        return "ERR_USERNAME_TAKEN"

    new_user = User(name, socket)
    users[name] = new_user
    return "OK_REG"

def create(room, socket):
    if room in rooms:
        return "ERR_ROOM_NAME_TAKEN"

    new_room = Room(room) 
    rooms[room] = new_room
    print "Created room: ", room
    return new_room.add_member(socket)

def join(room, socket):
    rm = rooms[room]
    print "Joined room: ", rooms
    return rm.add_member(socket)

def leave(room, socket):
    rm = rooms[room]
    print "Left room: ", rooms
    return rm.remove_member(socket)

def list_rooms():
    rms = ' '.join(rooms.keys())
    print "OK_LIST ", rms
    return ("OK_LIST " + rms)

def list_members(room):
    rm = rooms[room]
    members = rm.get_members()

    print "OK_MEMBERS ", ' '.join(members)
    return ("OK_MEMBERS " + ' '.join(members))
 
def send_message(room, socket, msg_lst):
    if room not in rooms:
        return "ERR_ROOM_NOT_EXIST"

    user = find_user(socket)
    if user:
        user_name = user.get_name()
        rm = rooms[room]
        if user_name in rm.get_members():
            return ("OK_MESSAGE " + user_name + ' ' + room + ' ' + ' '.join(msg_lst))
            # the msg content is needed in the return value for server to send to other users in the room
        else:
            return "ERR_NOT_IN_ROOM"
    else:
        return "ERR_USER_NOT_EXIST"

def quit(socket):
    return "OK_QUIT"
    
# helper function
def find_user(socket):
    for user in users.itervalues():
        if user.get_socket() == socket:
            return user
    return None

# dispatch functions - end
#####################################################

# data could be multiple messages queueing in the buffer, deliminated by '\n'
# Split these messages and store them in a list, dispatch each of them,
# store the return values in another list and return the list.
def dispatch_multi(data, socket):
    #TODO: change to a string ?
    ret = []
    multi_data = data.strip().split("\n")
    #print 'multi_data:', multi_data
    for dt in multi_data:
        resp = dispatch(dt, socket)
        if resp:
            ret.append(resp)
    return ret
            
        
def dispatch(data, socket):
    args = data.strip().split(" ")
    cmd = args[0]
    if len(args) > 1:
        param = args[1]

    if cmd == "REGISTER":
        return register(param, socket)
    elif cmd == "CREATE":
        return create(param, socket)
    elif cmd == "JOIN":
        return join(param, socket)
    elif cmd == "LEAVE":
        return leave(param, socket)
    elif cmd == "LIST":
        return list_rooms()
    elif cmd == "MEMBERS":
        return list_members(param)
    elif cmd == "MESSAGE":
        msg_lst = args[2:]
        return send_message(param, socket, msg_lst)
    elif cmd == "QUIT":
        return quit(socket)
    elif cmd == "PONG":
        # if receive a 'PONG' from some user, mark it as active
        user = find_user(socket)
        user.mark_active()
        pass
    else:
        return "ERR_INVALID"
    
def ping_clients(seconds):
    while True:
        # iterate all clients and send 'PING' to everyone.
	# TODO: dictionary changed size during iteration
        for user in users.itervalues():
            sckt = user.get_socket()
            sckt.send('PING\n')

	# give client 1 second to respond, if no response in 1 sec, consider the client as crashed
	sleep(1)
        for user in users.itervalues():
	    # if no 'PONG' was received, the client crashes, marked as inactive
	    if not user.is_active():
		# handle client crash
		handle_client_leave(user)               
	    # mark all the users as inactive for next round of PING
	    user.mark_inactive()

        sleep(seconds)

# called when a client sends "QUIT" or crashes
def handle_client_leave(user):
    if user:
        sckt = user.get_socket()
        sckt.close()
        
        name = user.get_name()
        rms = user.get_rooms()
        for rm in rms:
            room = rooms[rm]
            # remove the client from this room
            room.remove_member(sckt)

            # send message to other members of this room
            sckts = room.get_member_sockets()
            for s in sckts:
                print 'NOTICE user ' + name + ' has left\n'
                s.send('NOTICE user ' + name + ' has left\n')

        # remove client from user list
        del users[name]
#####################################################
# main function

def main():
    host = ''
    port = 8080
    backlog = 5
    size = 1024

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setblocking(0)
    server.bind((host,port))
    server.listen(backlog)
    print "Server is running on port 8080"

    thread = Thread(target = ping_clients, args = (1, ))
    thread.start()

    inputs = [server]
    running = 1
    while running:
        #ping_clients()
        readable, writable, exceptional = select.select(inputs,[],[])
        for s in readable:
            # if the socket is server socket
            # accept new client connection and add it to the connection list
            if s is server:
                connection, client_address = s.accept()
                connection.setblocking(0)
                inputs.append(connection)

            # if the socket is client socket
            # read data from the socket and process them
            else:
                try:
                    # use `try` `except` because if client closes the connection, 
                    # s.recv() here will cause error.
                    data = s.recv(size)
                    responses = dispatch_multi(data, s)
		    #print 'responses:', responses

                    for response in responses:
                        resp = response.split(' ')
			#print 'resp:', resp
                        status = resp[0]
                        # TODO: extract to a function
                        if status == "OK_MESSAGE":
                            s.send(status + "\n")
                            
                            # TODO: come up with a better variable name for "to_send", 
                            # it includes username, roomname, and the message body
                            to_send = ' '.join(resp[1:])

                            #user = resp[1]
                            room = resp[2]
                            print 'data:', data
                            for sckt in rooms[room].get_member_sockets():
                                sckt.send('MESSAGE ' + to_send + '\n')
			# if the client intentionally disconnect from server
                        elif status == "OK_QUIT":
                            s.send(status + "\n")
                            handle_client_leave(find_user(s))
                            inputs.remove(s)
                            # TODO Inform related users about this user's quit
                        else:
                            s.send(response + "\n")
		# if the socket is broken
                except socket.error:
                    handle_client_leave(find_user(s))
                    inputs.remove(s)

    server.close()

# main function - end
#####################################################

if __name__ == '__main__':
    main()

