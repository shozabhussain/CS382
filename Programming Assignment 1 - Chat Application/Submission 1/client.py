'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import getopt
import socket
import random
from threading import Thread
import os
import util


'''
Write your code inside this class. 
In the start() function, you will read user-input and act accordingly.
receive_handler() function is running another thread and you have to listen 
for incoming messages in this function.
'''

class Client:
    '''
    This is the main Client Class. 
    '''
    def __init__(self, username, dest, port, window_size):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        self.sock.bind(('', random.randint(10000, 40000)))
        self.name = username
        self.window = window_size
        self.check = True

    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message.
        Waits for userinput and then process it
        '''
        intialMsg = util.make_message("join:", 1, self.name)
        initialPacket = util.make_packet(msg=intialMsg)
        self.sock.sendto(initialPacket.encode("utf-8"), (self.server_addr, self.server_port))
        
        while self.check:
            
            msgToServer = input()
            
            if msgToServer == "list":
                makeMsg = util.make_message("request_users_list", 2)
                PacketToServer = util.make_packet(msg=makeMsg)
                self.sock.sendto(PacketToServer.encode("utf-8"), (self.server_addr, self.server_port))
                
            elif msgToServer.split()[0] == "msg":
                makeMsg = util.make_message("send_message", 4, msgToServer)
                PacketToServer = util.make_packet(msg=makeMsg)
                self.sock.sendto(PacketToServer.encode("utf-8"), (self.server_addr, self.server_port))
                
            elif msgToServer.split()[0] == "file":
                
                filename = util.listToString(msgToServer.split()[(2+int(msgToServer.split()[1])):len(msgToServer)])
                file = open(filename)
                fileData = file.read()
                msgToServer = msgToServer + " " + fileData
                makeMsg = util.make_message("send_file", 4, msgToServer)
                PacketToServer = util.make_packet(msg=makeMsg)
                self.sock.sendto(PacketToServer.encode("utf-8"), (self.server_addr, self.server_port))
                            
            elif msgToServer == "quit":
                makeMsg = util.make_message("disconnect", 2)
                PacketToServer = util.make_packet(msg=makeMsg)
                self.sock.sendto(PacketToServer.encode("utf-8"), (self.server_addr, self.server_port))
                print("quitting")
                self.sock.close()
                self.check=False
               
            elif msgToServer == "help":
                print("FORMAT:")
                print("Message: msg <number_of_users> <username1> <username2> ... <message>")
                print("Available Users: list")
                print("File Sharing: file <number_of_users> <username1> <username2> ... <file_name>")
                print("Quit: quit")
                   
            else:   
                print("incorrect userinput format")

    def receive_handler(self):
        '''
        Waits for a message from server and process it accordingly
        '''
        while self.check:
            
            message, address = self.sock.recvfrom(4096)
            _, _, msg, _ = util.parse_packet(message.decode("utf-8"))
            
            
            if msg.split()[0] == "ERR_USERNAME_UNAVAILABLE":
                print("disconnected: username not available")
                self.sock.close()
                self.check=False
                return
                
            elif msg.split()[0] == "ERR_SERVER_FULL":
                print("disconnected: server full")
                self.sock.close()
                self.check=False
                return
            
            elif msg.split()[0] == "response_users_list":
                print(util.listToString(msg.split()[2:]))
           
            elif msg.split()[0] == "forward_message":
                print(util.listToString(msg.split()[2:]))
                
            elif msg.split()[0] == "forward_file":
                print(util.listToString(msg.split()[2:5]))
                filename = self.name + "_" + msg.split()[4]
                fileData = util.listToString(msg.split()[5:])
                file = open(filename, "w")
                file.write(fileData)
                file.close()
                
            elif msg.split()[0] == "disconnect":
                print("disconnected: server received an unknown command")
                self.sock.close()
                self.check=False
                return
                

# Do not change this part of code
if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our Client module completion
        '''
        print("Client")
        print("-u username | --user=username The username of Client")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW_SIZE | --window=WINDOW_SIZE The window_size, defaults to 3")
        print("-h | --help Print this help")
    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "u:p:a:w", ["user=", "port=", "address=","window="])
    except getopt.error:
        helper()
        exit(1)

    PORT = 15000
    DEST = "localhost"
    USER_NAME = None
    WINDOW_SIZE = 3
    for o, a in OPTS:
        if o in ("-u", "--user="):
            USER_NAME = a
        elif o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW_SIZE = a

    if USER_NAME is None:
        print("Missing Username.")
        helper()
        exit(1)

    S = Client(USER_NAME, DEST, PORT, WINDOW_SIZE)
    try:
        # Start receiving Messages
        T = Thread(target=S.receive_handler)
        T.daemon = True
        T.start()
        # Start Client
        S.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
