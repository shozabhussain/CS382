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

    def send_packet(self, initial_msg, address):

        '''function to send a make into chunks'''

        sequence_number = random.randint(0,100)
        start_packet = util.make_packet(msg_type="start", seqno=sequence_number, msg="")
        self.sock.sendto(start_packet.encode("utf-8"), address)
        chunk_of_string = util.str_to_chunks(initial_msg, util.CHUNK_SIZE)

        for item in range(0,len(chunk_of_string)):

            sequence_number = sequence_number + 1
            packet_to_client = util.make_packet(msg_type="data", seqno=int(sequence_number), msg=chunk_of_string[item])
            self.sock.sendto(packet_to_client.encode("utf-8"), address)

        end_packet = util.make_packet(msg_type="end", seqno=int(sequence_number)+1)
        self.sock.sendto(end_packet.encode("utf-8"), address)

    def handle_client(self, address_key):

        '''function to handle a client'''

        while True:

            message, address = self.queue_dict[address_key].get()
            msg_type, seqno, msg_recv, _ = util.parse_packet(message.decode("utf-8"))

            if msg_type == "ack":
                self.seq_number = seqno
                continue

            if msg_type in ('start', 'data'):

                if msg_type == "start":
                    msg = ""

                msg = msg + msg_recv
                ack_packet = util.make_packet(msg_type="ack", seqno=int(seqno)+1)
                self.sock.sendto(ack_packet.encode("utf-8"), address)
                continue

            if msg_type == "end":
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

            if address not in self.queue_dict.keys():
                client_queue = queue.Queue()
                client_queue.put( (message, address) )
                self.queue_dict[address] = client_queue
                threading.Thread(target = self.handle_client, args = (address, )).start()

            elif address in self.queue_dict.keys():
                self.queue_dict[address].put( (message, address) )

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
