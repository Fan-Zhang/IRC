import select
import socket
import sys

# TODO:
# 1. REMOVE EMPTY ROOM
# 2. PING - Server can gracefully handle client crashes
# 3. Create another thread to ping the clients periodically
# 4. QUIT

#####################################################
# User Class
#####################################################

class User:
    def __init__(self, name, socket):
        self.name = name
        self.socket = socket
        self.rooms = []  # list of room names

    def getName(self):
        return self.name

    def getRooms(self):
        return self.rooms

    def getSocket(self):
        return self.socket

    def joinRoom(self, room):
        if room in self.rooms:
            return "ERR_ALREADY_IN_ROOM"
        else:
            self.rooms.append(room)
            return "OK_JOIN_ROOM"

    def leaveRoom(self, room):
        if room not in self.rooms:
            return "ERR_NOT_IN_ROOM"
        else:
            self.rooms.remove(room)
            return "OK_LEAVE_ROOM"


#####################################################
# globals
#####################################################
users = set()  # a set of User objects
rooms = {}  # a dictionary - key: room name  value: set of sockets

def register(name, socket):
    for user in users:
        if user.getName() == name:
            return "ERR_USERNAME_TAKEN"

    newUser = User(name, socket)
    users.add(newUser)
    return "OK_REG"

def create(room, socket):
    if room in rooms:
        return "ERR_ROOM_NAME_TAKEN"

    for user in users:
        if user.getSocket() == socket:
            rooms[room] = {socket}
            print ("Created room: ", room)
            return user.joinRoom(room)

    print ("User not exist")
    return "ERR_USER_NOT_EXIST"

def join(room, socket):
    if room not in rooms:
        return "ERR_ROOM_NOT_EXIST"

    for user in users:
        if user.getSocket() == socket:
            rooms[room].add(socket)
            print ("Joined room: ", rooms)
            return user.joinRoom(room)

    return "ERR_USER_NOT_EXIST"

def leave(room, socket):
    if room not in rooms:
        return "ERR_ROOM_NOT_EXIST"

    for user in users:
        if user.getSocket() == socket:
            rooms[room].remove(socket)
            print ("Left room: ", rooms)
            return user.leaveRoom(room)

    return "ERR_USER_NOT_EXIST"


def listRooms():
    rms = ' '.join(rooms.keys())
    print "OK_LIST "+rms
    return ("OK_LIST "+rms)

def listMembers(room):
    members = []
    sockets = rooms[room]
    # TODO
    for socket in sockets:
        for user in users:
            if user.getSocket() == socket:
                members.append(user.getName())
    print "OK_MEMBERS "+' '.join(members)
    return ("OK_MEMBERS "+' '.join(members))
 
def messageTo(room, socket):
    if room not in rooms:
        return "ERR_ROOM_NOT_EXIST"

    for user in users:
        if user.getSocket() == socket:
            return ("OK_MESSAGE " + user.getName() + ' ' + room)

    return "ERR_USER_NOT_EXIST"


def dispatch(data, socket):
    args = data.split(" ")
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
        return listRooms()
    elif cmd == "MEMBERS":
        return listMembers(info)
    elif cmd == "MESSAGE":
        return messageTo(info, socket)
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
