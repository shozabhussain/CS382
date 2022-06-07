'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util


class Server:
    '''
    This is the main Server Class. You will to write Server code inside this class.
    '''
    def __init__(self, dest, port, window):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))
        self.window = window
        self.onlineUsers = {}

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it
        '''
        while True:
            message, address = self.sock.recvfrom(4096)
            _, _, msg, _ = util.parse_packet(message.decode("utf-8"))
            splitMsg = msg.split()
            
            if splitMsg[0] == "join:":
                if len(self.onlineUsers) < util.MAX_NUM_CLIENTS:
                    
                    
                    if splitMsg[2] in self.onlineUsers.keys():
                        self.sock.sendto("ERR_USERNAME_UNAVAILABLE".encode("utf-8"), address)
                        
                    else:
                        self.onlineUsers[splitMsg[2]] = address
                        print("join:", splitMsg[2])
                        
                else:
                    self.sock.sendto("ERR_SERVER_FULL".encode("utf-8"), address)
            
            elif splitMsg[0] == "request_users_list":
                nameOfSender = list(self.onlineUsers.keys())[list(self.onlineUsers.values()).index(address)]
                listOfUsers = list(self.onlineUsers.keys())
                listOfUsers.sort()
                msgToSend = "list: " + util.listToString(listOfUsers)
                makeMsg = util.make_message("response_users_list", 3, msgToSend)
                packetToClient = util.make_packet(msg=makeMsg)
                self.sock.sendto(packetToClient.encode("utf-8"), address)
                print("request_users_list:", nameOfSender)
                
            elif splitMsg[0] == "send_message":
                nameOfSender = list(self.onlineUsers.keys())[list(self.onlineUsers.values()).index(address)]
                
                if not splitMsg[3].isdigit():
                    print("disconnected:", nameOfSender, "sent unknown command")
                    makeMsg = util.make_message("disconnect", 2)
                    packetToClient = util.make_packet(msg=makeMsg)
                    self.sock.sendto(packetToClient.encode("utf-8"), address)
                    self.onlineUsers.pop(nameOfSender)
                    continue
                
                if int(splitMsg[3]) < 1 or int(splitMsg[3]) > util.MAX_NUM_CLIENTS or int(splitMsg[3]) > len(splitMsg) - 5 :
                    print("disconnected:", nameOfSender, "sent unknown command")
                    makeMsg = util.make_message("disconnect", 2)
                    packetToClient = util.make_packet(msg=makeMsg)
                    self.sock.sendto(packetToClient.encode("utf-8"), address)
                    self.onlineUsers.pop(nameOfSender)
                    continue
                               
                print("msg:", nameOfSender)
                msgToSend = "msg: " + nameOfSender + ": " + util.listToString(splitMsg[(4+int(splitMsg[3])):len(splitMsg)])
                
                for i in range(4, 4+int(splitMsg[3])):
                    if splitMsg[i] in self.onlineUsers.keys():
                        makeMsg = util.make_message("forward_message", 4, msgToSend)
                        packetToClient = util.make_packet(msg=makeMsg)
                        self.sock.sendto(packetToClient.encode("utf-8"), self.onlineUsers[splitMsg[i]])
                         
                    else:
                        print("msg:", nameOfSender, "to non-existent user", splitMsg[i])
                        
                        
            elif splitMsg[0] == "send_file":
                nameOfSender = list(self.onlineUsers.keys())[list(self.onlineUsers.values()).index(address)]   
                
                if not splitMsg[3].isdigit():
                    print("disconnected:", nameOfSender, "sent unknown command")
                    makeMsg = util.make_message("disconnect", 2)
                    packetToClient = util.make_packet(msg=makeMsg)
                    self.sock.sendto(packetToClient.encode("utf-8"), address)
                    self.onlineUsers.pop(nameOfSender)
                    continue
                
                if int(splitMsg[3]) < 1 or int(splitMsg[3]) > util.MAX_NUM_CLIENTS or int(splitMsg[3]) > len(splitMsg) - 5:
                    print("disconnected:", nameOfSender, "sent unknown command")
                    makeMsg = util.make_message("disconnect", 2)
                    packetToClient = util.make_packet(msg=makeMsg)
                    self.sock.sendto(packetToClient.encode("utf-8"), address)
                    self.onlineUsers.pop(nameOfSender)
                    continue
                
                print("file:", nameOfSender)
                msgToSend = "file: " + nameOfSender + ": " + util.listToString(splitMsg[(4+int(splitMsg[3])):len(splitMsg)])
                makeMsg = util.make_message("forward_file", 4, msgToSend)
                packetToClient = util.make_packet(msg=makeMsg)
                
                for i in range(4, 4+int(splitMsg[3])):
                    if splitMsg[i] in self.onlineUsers.keys():
                         self.sock.sendto(packetToClient.encode("utf-8"), self.onlineUsers[splitMsg[i]])
                         
                    else:
                        print("file:", nameOfSender, "to non-existent user", splitMsg[i])
                
            elif splitMsg[0] == "disconnect":
                nameOfSender = list(self.onlineUsers.keys())[list(self.onlineUsers.values()).index(address)]
                print("disconnected:", nameOfSender)
                self.onlineUsers.pop(nameOfSender)
        

# Do not change this part of code

if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our module completion
        '''
        print("Server")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW | --window=WINDOW The window size, default is 3")
        print("-h | --help Print this help")

    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "p:a:w", ["port=", "address=","window="])
    except getopt.GetoptError:
        helper()
        exit()

    PORT = 15000
    DEST = "localhost"
    WINDOW = 3

    for o, a in OPTS:
        if o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW = a

    SERVER = Server(DEST, PORT,WINDOW)
    try:
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
