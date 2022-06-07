'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import random
import queue
import threading
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
        self.online_users = {}
        self.queue_dict = {}
        self.seq_number = 0
        self.acks_dict = {}

    def send_packet(self, initial_msg, address):

        '''function to send a make into chunks'''

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
                        self.sock.sendto(packets_dict[ (acks_recv[-1] + i) ].encode("utf-8"), address)
                        
                        i = i + 1
                        continue
                    else:
                        break

                send_window = False

            try:
                message, address = self.acks_dict[address].get(timeout=util.TIME_OUT)

            except:
                send_window = True

                while not packets_window.empty():
                    packets_window.get()

                continue

            msg_type, seqno, msg_recv, _ = util.parse_packet(message.decode("utf-8"))
            lastest_ack = int(seqno)
            

            if lastest_ack == sequence_number + 1:

                while not self.acks_dict[address].empty():
                    self.acks_dict[address].get()
                
                return

            if lastest_ack - acks_recv[-1] == 0:
                
                continue

            if lastest_ack - acks_recv[-1] >= 1:
                acks_recv.append(lastest_ack)
                packets_window.get()

                if (acks_recv[-1] + self.window -1) in packets_dict.keys():
                    self.sock.sendto(packets_dict[acks_recv[-1] + self.window - 1].encode("utf-8"), address)
                    packets_window.put(acks_recv[-1] + self.window - 1)
                  
                continue

    def handle_client(self, address_key):

        '''function to handle a client'''

        packets_list = []
        packets_recv = queue.PriorityQueue()

        while True:

            message, address = self.queue_dict[address_key].get()
            msg_type, seqno, msg_recv, _ = util.parse_packet(message.decode("utf-8"))

            sequence_number = int(seqno)

            if msg_type == "start":
                msg = ""
                packets_list.append(sequence_number)
                ack_packet = util.make_packet(msg_type="ack", seqno= sequence_number + 1)
                self.sock.sendto(ack_packet.encode("utf-8"), address)
                continue

            if len(packets_list) == 0:
                continue

            if sequence_number - packets_list[-1] != 1:
                ack_packet = util.make_packet(msg_type="ack", seqno= packets_list[-1] + 1 )
                self.sock.sendto(ack_packet.encode("utf-8"), address)
                continue

            else:
                if msg_type == "data":
                    packets_list.append(sequence_number)
                    packets_recv.put( (sequence_number, msg_recv) )
                    ack_packet = util.make_packet(msg_type="ack", seqno= sequence_number + 1 )
                    self.sock.sendto(ack_packet.encode("utf-8"), address)
                    continue
            
                if msg_type == "end":
                    packets_list.append(sequence_number)
                    ack_packet = util.make_packet(msg_type="ack", seqno= sequence_number + 1)
                    self.sock.sendto(ack_packet.encode("utf-8"), address)
                    packets_list.clear()

                    while not packets_recv.empty():
                        msg = msg + packets_recv.get()[1]

                    split_msg = msg.split()

                    if split_msg[0] == "join:":
                        if len(self.online_users) < util.MAX_NUM_CLIENTS:

                            if split_msg[2] in self.online_users.keys():
                                make_msg = util.make_message("err_username_unavailable", 2)
                                self.send_packet(make_msg,address)
                                return

                            self.online_users[split_msg[2]] = address
                            print("join:", split_msg[2])

                        else:
                            make_msg = util.make_message("err_server_full", 2)
                            self.send_packet(make_msg, address)
                            return

                    elif split_msg[0] == "request_users_list":
                        name_of_sender = list(self.online_users.keys())[list(self.online_users.values()).index(address)]
                        list_of_user = list(self.online_users.keys())
                        list_of_user.sort()
                        msg_to_send = "list: " + util.list_to_string(list_of_user)
                        make_msg = util.make_message("response_users_list", 3, msg_to_send)
                        self.send_packet(make_msg, address)
                        print("request_users_list:", name_of_sender)

                    elif split_msg[0] == "send_message":
                        name_of_sender = list(self.online_users.keys())[list(self.online_users.values()).index(address)]

                        if not split_msg[3].isdigit():
                            print("disconnected:", name_of_sender, "sent unknown command")
                            make_msg = util.make_message("disconnect", 2)
                            self.send_packet(make_msg, address)
                            self.online_users.pop(name_of_sender)
                            return

                        if int(split_msg[3]) < 1 or int(split_msg[3]) > util.MAX_NUM_CLIENTS or int(split_msg[3]) > len(split_msg) - 5 :
                            print("disconnected:", name_of_sender, "sent unknown command")
                            make_msg = util.make_message("disconnect", 2)
                            self.send_packet(make_msg, address)
                            self.online_users.pop(name_of_sender)
                            return

                        print("msg:", name_of_sender)
                        msg_to_send = "msg: " + name_of_sender + ": " + util.list_to_string(split_msg[(4+int(split_msg[3])):len(split_msg)])

                        for i in range(4, 4+int(split_msg[3])):
                            if split_msg[i] in self.online_users.keys():
                                make_msg = util.make_message("forward_message", 4, msg_to_send)
                                self.send_packet(make_msg, self.online_users[split_msg[i]] )

                            else:
                                print("msg:", name_of_sender, "to non-existent user", split_msg[i])


                    elif split_msg[0] == "send_file":
                        name_of_sender = list(self.online_users.keys())[list(self.online_users.values()).index(address)]

                        if not split_msg[3].isdigit():
                            print("disconnected:", name_of_sender, "sent unknown command")
                            make_msg = util.make_message("disconnect", 2)
                            self.send_packet(make_msg, address)
                            self.online_users.pop(name_of_sender)
                            return

                        if int(split_msg[3]) < 1 or int(split_msg[3]) > util.MAX_NUM_CLIENTS or int(split_msg[3]) > len(split_msg) - 5:
                            print("disconnected:", name_of_sender, "sent unknown command")
                            make_msg = util.make_message("disconnect", 2)
                            self.send_packet(make_msg, address)
                            self.online_users.pop(name_of_sender)
                            return

                        print("file:", name_of_sender)
                        msg_to_send = "file: " + name_of_sender + ": " + util.list_to_string(split_msg[(4+int(split_msg[3])):len(split_msg)])
                        make_msg = util.make_message("forward_file", 4, msg_to_send)

                        for i in range(4, 4+int(split_msg[3])):
                            if split_msg[i] in self.online_users.keys():
                                self.send_packet(make_msg, self.online_users[split_msg[i]])
                            else:
                                print("file:", name_of_sender, "to non-existent user", split_msg[i])

                    elif split_msg[0] == "disconnect":
                        name_of_sender = list(self.online_users.keys())[list(self.online_users.values()).index(address)]
                        print("disconnected:", name_of_sender)
                        self.online_users.pop(name_of_sender)
                        return

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it
        '''

        while True:
            message, address = self.sock.recvfrom(4096)
            msg_type, seqno, msg_recv, _ = util.parse_packet(message.decode("utf-8"))

            if msg_type == "ack":
                
                self.acks_dict[address].put( (message, address) )
                continue

            if address not in self.queue_dict.keys():
                client_queue = queue.Queue()
                client_queue.put( (message, address) )
                self.queue_dict[address] = client_queue

                acks_queue = queue.Queue()
                self.acks_dict[address] = acks_queue

                threading.Thread(target = self.handle_client, args = (address, )).start()
                continue

            elif address in self.queue_dict.keys():
                self.queue_dict[address].put( (message, address) )
                continue

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
