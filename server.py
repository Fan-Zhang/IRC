import select
import socket
import sys

# TODO:
# 1. REMOVE EMPTY ROOM
# 2. PING - Server can gracefully handle client crashes
# 3. Create another thread to ping the clients periodically
# 4. QUIT
# 5. class Room
# 6. extract validation of user and room
# 7. use socket to get user name (in listMembers())
# 8. error handling when no `info`

#####################################################
# User Class

class User:
    def __init__(self, name, socket):
        self.name = name
        self.socket = socket
        self.rooms = []  # a list of rooms the user is in

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
 
def send_message(room, socket):
    if room not in rooms:
        return "ERR_ROOM_NOT_EXIST"

    user = find_user(socket)
    if user:
        return ("OK_MESSAGE " + user.get_name() + ' ' + room)
    else:
        return "ERR_USER_NOT_EXIST"

# helper function
def find_user(socket):
    for user in users:
        if user.get_socket() == socket:
            return user
    return None

# dispatch functions - end
#####################################################


def dispatch(data, socket):
    args = data.split(" ")
    cmd = args[0]
    if len(args) > 1:
        info = args[1]
    # TODO: error handling when `info` does not exist

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
        return send_message(info, socket)
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
                        resp = response.split(' ')
                        status = resp[0]
                        if status == "OK_MESSAGE":
                            print data
                            s.send(status)
                            user = resp[1]
                            room = resp[2]
                            for sckt in rooms[room]:
                                sckt.send(data + ' ' + user)
                        else:
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
