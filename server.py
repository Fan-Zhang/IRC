import select
import socket
import sys
from threading import Thread
from time import sleep

# TODO:
# 1. REMOVE EMPTY ROOM
# 2. PING - Server can gracefully handle client crashes
# 3. Create another thread to ping the clients periodically
# 4. QUIT
# 5. class Room
# 6. extract validation of user and room
# 7. use socket to get user name (in listMembers())
# 8. If the user has already registered, and sends “REGISTER xx” again, 
#    server should return some error code. Currently this behavior causes crash in server.
# 9. Other members of the room should get noticed when a client has left
#10. Check if the user is in the room before removing them from the room if they send “LEAVE xx”.


#####################################################
# User Class

class User:
    def __init__(self, name, socket):
        self.name = name
        self.socket = socket
        self.rooms = []  # a list of rooms the user is in
        self.active = True  # if the user is still connected

    def get_name(self):
        return self.name

    def get_rooms(self):
        return self.rooms

    def get_socket(self):
        return self.socket

    def join_room(self, room):
        if room in self.rooms:
            return "ERR_ALREADY_IN_ROOM"
        else:
            self.rooms.append(room)
            return "OK_JOIN_ROOM"

    def leave_room(self, room):
        if room not in self.rooms:
            return "ERR_NOT_IN_ROOM"
        else:
            self.rooms.remove(room)
            return "OK_LEAVE_ROOM"
        
    # mark the user as active
    def mark_active(self):
        self.active = True
    
    # mark the user as inactive
    def mark_inactive(self):
        self.active = False
    
    # check if the user is active
    def check_active(self):
        return self.active

# User Class - end
#####################################################


#####################################################
# globals

users = set()  # a set of User objects
rooms = {}  # a dictionary:  key - room name; value - set of sockets

# globals - end
#####################################################


#####################################################
# dispatch functions

def register(name, socket):
    for user in users:
        if user.get_name() == name:
            return "ERR_USERNAME_TAKEN"

    newUser = User(name, socket)
    users.add(newUser)
    return "OK_REG"

def create(room, socket):
    if room in rooms:
        return "ERR_ROOM_NAME_TAKEN"

    user = find_user(socket)
    if user:
        rooms[room] = {socket}
        print "Created room: ", room
        return user.join_room(room)
    else:
        print "User not exist"
        return "ERR_USER_NOT_EXIST"

def join(room, socket):
    if room not in rooms:
        return "ERR_ROOM_NOT_EXIST"

    user = find_user(socket)
    if user:
        rooms[room].add(socket)
        print "Joined room: ", rooms
        return user.join_room(room)
    else:
        return "ERR_USER_NOT_EXIST"

def leave(room, socket):
    if room not in rooms:
        return "ERR_ROOM_NOT_EXIST"

    user = find_user(socket)
    if user:
        rooms[room].remove(socket)
        print "Left room: ", rooms
        return user.leave_room(room)
    else:
        return "ERR_USER_NOT_EXIST"

def list_rooms():
    rms = ' '.join(rooms.keys())
    print "OK_LIST ", rms
    return ("OK_LIST " + rms)

def list_members(room):
    members = []
    sockets = rooms[room]  # the set of sockets
    # TODO: how to better finding user name through user socket - a Room class ??
    for socket in sockets:
        user = find_user(socket)
        if user:
            members.append(user.get_name())

    print "OK_MEMBERS ", ' '.join(members)
    return ("OK_MEMBERS " + ' '.join(members))
 
def send_message(room, socket, msg_lst):
    if room not in rooms:
        return "ERR_ROOM_NOT_EXIST"

    # TODO: Check if user is in this room
    user = find_user(socket)
    if user:
        return ("OK_MESSAGE " + user.get_name() + ' ' + room + ' ' + ' '.join(msg_lst))
        # the msg content is needed in the return value for server to send to other users in the room
    else:
        return "ERR_USER_NOT_EXIST"

def quit(socket):
    return "OK_QUIT"
    
# helper function
def find_user(socket):
    for user in users:
        if user.get_socket() == socket:
            return user
    return None

# dispatch functions - end
#####################################################

# data could be multiple messages queueing in the buffer, deliminated by '\n'
# Split these messages and store in a list, dispatch each of them, store the 
# return values in aother list, and return the list.
def dispatch_multi(data, socket):
    ret = []
    multi_data = data.strip().split("\n")
    print multi_data
    for dt in multi_data:
        resp = dispatch(dt, socket)
        if resp:
            ret.append(resp)
    return ret
            
        
def dispatch(data, socket):
    args = data.strip().split(" ")
    cmd = args[0]
    if len(args) > 1:
        info = args[1]

    if cmd == "REGISTER":
        return register(info, socket)
    elif cmd == "CREATE":
        return create(info, socket)
    elif cmd == "JOIN":
        return join(info, socket)
    elif cmd == "LEAVE":
        return leave(info, socket)
    elif cmd == "LIST":
        return list_rooms()
    elif cmd == "MEMBERS":
        return list_members(info)
    elif cmd == "MESSAGE":
        msg_lst = args[2:]
        return send_message(info, socket, msg_lst)
    elif cmd == "QUIT":
        return quit(socket)
    elif cmd == "PONG":
        print 'dispatch', cmd
        # if receive a 'PONG' from some user, mark it as active
        user = find_user(socket)
        user.mark_active()
        pass
    else:
        print 'dispatch', cmd
        return "ERR_INVALID"
    
def ping_clients():
    # iterate all clients and send 'PING' to everyone.
    for user in users:
        sckt = user.get_socket()
        sckt.send('PING\n')
        print 'ping_clients'

        #resp = sckt.recv(size)
    sleep(1)
    for user in users:
        if user.check_active() == False:
            # if any user is inactive, it means no 'PONG' was received 
            # last round from its socket. so client crashed
            # handle client left situation 
            handle_client_leave(user)               
        # mark all the users as inactive for next round of PING
        user.mark_inactive()

# this function is called when a user sends "QUIT", 
# or when a client is crashed 
def handle_client_leave(user):
    if user:
        sckt = user.get_socket()
        sckt.close()
        # remove client from user list
        users.remove(user)
        
        rms = user.get_rooms()
        name = user.get_name()
        for room in rms:
            sckts = rooms[room]
            # remove the client from this room
            sckts.remove(sckt)

            # send message to other members of this room
            for s in sckts:
                s.send('NOTICE user ' + name + ' has left\n')


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
    inputs = [server]
    running = 1
    while running:
        ping_clients()
        readable, writable, exceptional = select.select(inputs,[],[])
        for s in readable:
            # if the socket is server socket
            # accept new client connection and add it to the connection list
            if s is server:
                connection, client_address = s.accept()
                #connection.setblocking(0)
                inputs.append(connection)

            # if the socket is client socket
            # read data from the socket and process them
            else:
                try:
                    # used try except because if client closes the connection, 
                    # s.recv() here will cause error.

                    data = s.recv(size)
                    responses = dispatch_multi(data, s)
                    #if response:
                    for response in responses:
                        resp = response.split(' ')
                        status = resp[0]
                        # TODO: extract to a function
                        if status == "OK_MESSAGE":
                            s.send(status + "\n")
                            
                            # TODO: come up with a better variable name for "to_send", 
                            # it includes username, roomname, and the message body
                            to_send = ' '.join(resp[1:])

                            #user = resp[1]
                            room = resp[2]
                            print data
                            for sckt in rooms[room]:
                                #sckt.send(data + ' ' + user + '\n')
                                sckt.send('MESSAGE ' + to_send + '\n')
                        elif status == "OK_QUIT":
                            s.send(status + "\n")
                            handle_client_leave(find_user(s))
                            inputs.remove(s)
                            # TODO Inform related users about this user's quit
                        else:
                            print response
                            s.send(response +"\n")
                    # if no valid response for this request
                    # continue to the next client
                    # else:
                    #    continue
                except socket.error:
                    handle_client_leave(find_user(s))
                    inputs.remove(s)

    server.close()

# main function - end
#####################################################

if __name__ == '__main__':
    main()

