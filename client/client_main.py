import sys
import socket

def main():
    client = Client()
    client.respondToServer()

class Client:

    def __init__(self):
        self.port = 8080
        self.host = 'localhost'
        
		# Attempt to connect to server
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            sys.stdout.write('Successfully Connected to Server\n')
        except:
            sys.stdout.write('Failed to Connect to Server')
            
    def sendMessage(self, message):
        return self.socket.send(message)
    def respondToServer(self):
        while True:
            data = self.socket.recv(100)
            if data == 'Please provide a user name: \n':
                # server asks user name for the first time 
                # send user name to server
                sys.stdout.write(data)
                self.name = sys.stdin.readline()
                self.sendMessage(self.name)
            elif data == 'Name used\n':
                # server rejects an existed name and ask for a new one
                # send user name to server when server rejects an existed name
                sys.stdout.write(data)
                self.name = sys.stdin.readline()
                self.sendMessage(self.name)
            else:
                # display received message
                sys.stdout.write(data)
            
                 
            


if __name__ == '__main__':
    main()
