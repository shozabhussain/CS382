'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import getopt
import socket
import random
from threading import Thread
import os
import queue
import util

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
        self.transfer_queue = queue.Queue()

    def send_packet(self, initial_msg):

        '''function to send messages into chunks'''

        packets_dict = {}
        acks_recv = []

        sequence_number = random.randint(0,100)
        acks_recv.append(sequence_number)
        
        start_packet = util.make_packet(msg_type="start", seqno=sequence_number, msg="")
        packets_dict[sequence_number] = start_packet
        sequence_number = sequence_number + 1

        chunk_of_string = util.str_to_chunks(initial_msg, util.CHUNK_SIZE)

        for item in range(0,len(chunk_of_string)):

            packet_to_server = util.make_packet(msg_type="data", seqno=int(sequence_number), msg=chunk_of_string[item])
            packets_dict[sequence_number] = packet_to_server
            sequence_number = sequence_number + 1

        end_packet = util.make_packet(msg_type="end", seqno=sequence_number , msg="")
        packets_dict[sequence_number] = end_packet

        packets_window = queue.Queue()
        send_window = True

        
        while True:

            if send_window == True:
                i = 0

                while i!= self.window and i!=len(packets_dict.keys()) :

                    if (acks_recv[-1] + i) in packets_dict.keys():
                        packets_window.put( (acks_recv[-1] + i) )
                        self.sock.sendto(packets_dict[ (acks_recv[-1] + i) ].encode("utf-8"), (self.server_addr, self.server_port))
                        
                        i = i + 1
                        continue
                    else:
                        break

                send_window = False

            try:
                lastest_ack = (self.transfer_queue.get(timeout=util.TIME_OUT))

            except:
                send_window = True

                while not packets_window.empty():
                    packets_window.get()

                continue

            lastest_ack = int(lastest_ack)
            

            if lastest_ack == sequence_number + 1:

                while not self.transfer_queue.empty():
                    self.transfer_queue.get()

                return

            if lastest_ack - acks_recv[-1] == 0:
               
                continue

            if lastest_ack - acks_recv[-1] >= 1:
                acks_recv.append(lastest_ack)
                packets_window.get()

                if (acks_recv[-1] + self.window -1) in packets_dict.keys():
                    self.sock.sendto(packets_dict[acks_recv[-1] + self.window - 1].encode("utf-8"), (self.server_addr, self.server_port))
                    packets_window.put(acks_recv[-1] + self.window - 1)
                  
                continue



    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message.
        Waits for userinput and then process it
        '''

        initial_msg = util.make_message("join:", 1, self.name)
        self.send_packet(initial_msg)

        while self.check:

            msg_to_server = input()
            
            if msg_to_server == "list":
                make_msg = util.make_message("request_users_list", 2)
                self.send_packet(make_msg)

            elif msg_to_server.split()[0] == "msg":
                make_msg = util.make_message("send_message", 4, msg_to_server)
                self.send_packet(make_msg)

            elif msg_to_server.split()[0] == "file":

                filename = util.list_to_string(msg_to_server.split()[(2+int(msg_to_server.split()[1])):len(msg_to_server)])
                file = open(filename)
                file_data = file.read()
                msg_to_server = msg_to_server + " " + file_data
                make_msg = util.make_message("send_file", 4, msg_to_server)
                self.send_packet(make_msg)

            elif msg_to_server == "quit":
                make_msg = util.make_message("disconnect", 2)
                self.send_packet(make_msg)
                print("quitting")
                self.sock.close()
                self.check=False

            elif msg_to_server == "help":
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
        acks_recv = []
        #overhead_packets = []
        packets_recv = queue.PriorityQueue()
        msg = ""
        while self.check:

            message, address = self.sock.recvfrom(4096)
            msg_type, seqno, msg_recv, _ = util.parse_packet(message.decode("utf-8"))
            sequence_number = int(seqno)

            if msg_type == "ack":

                self.transfer_queue.put(seqno)
                continue

            if msg_type == "start":
                msg = ""
                acks_recv.append(sequence_number)
                ack_packet = util.make_packet(msg_type="ack", seqno= sequence_number + 1)
                self.sock.sendto(ack_packet.encode("utf-8"), (self.server_addr, self.server_port))
                continue

            if len(acks_recv) == 0:
                continue

            if sequence_number - acks_recv[-1] != 1:
                ack_packet = util.make_packet(msg_type="ack", seqno= acks_recv[-1] + 1 )
                self.sock.sendto(ack_packet.encode("utf-8"), (self.server_addr, self.server_port))
                continue

            else:
                if msg_type == "data":
                    acks_recv.append(sequence_number)
                    packets_recv.put( (sequence_number, msg_recv) )
                    ack_packet = util.make_packet(msg_type="ack", seqno= sequence_number + 1 )
                    self.sock.sendto(ack_packet.encode("utf-8"), (self.server_addr, self.server_port))
                    continue


                if msg_type == "end":
                    acks_recv.append(sequence_number)
                    ack_packet = util.make_packet(msg_type="ack", seqno= sequence_number + 1)
                    self.sock.sendto(ack_packet.encode("utf-8"), (self.server_addr, self.server_port))
                    acks_recv.clear()

                    while not packets_recv.empty():
                        msg = msg + packets_recv.get()[1]

                    if msg.split()[0] == "err_username_unavailable":
                        print("disconnected: username not available")
                        self.sock.close()
                        self.check=False
                        return

                    if msg.split()[0] == "err_server_full":
                        print("disconnected: server full")
                        self.sock.close()
                        self.check=False
                        return

                    if msg.split()[0] == "response_users_list":
                        print(util.list_to_string(msg.split()[2:]))

                    elif msg.split()[0] == "forward_message":
                        print(util.list_to_string(msg.split()[2:]))

                    elif msg.split()[0] == "forward_file":
                        print(util.list_to_string(msg.split()[2:5]))
                        filename = self.name + "_" + msg.split()[4]
                        file_data = util.list_to_string(msg.split()[5:])
                        file = open(filename, "w")
                        file.write(file_data)
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
