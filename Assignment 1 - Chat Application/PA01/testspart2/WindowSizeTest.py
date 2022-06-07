import hashlib
import os
import random
from string import ascii_letters
import time
from testspart2 import BasicTest
import util

class WindowSizeTest(BasicTest.BasicTest):
    def set_state(self):
        self.num_of_clients = 4
        self.client_stdin = {"client1": 1, "client2":2}
        self.input = [  
                        ("client1","file 1 client2 test_file2\n") ,
                     ]
        self.time_interval = 3
        self.num_of_acks = 8*2 + 2*2 +  2*2 
        with open("test_file2","w") as f:
            f.write(''.join(random.choice(ascii_letters) for i in range(10000)))
        self.last_time = time.time()
        self.packets_ = {'client1':[],'client2':[]}
        self.last_ack_dropped = []
        self.checksum_test = {'client1':False,'client2':False}
        self.window = 3

    def result(self):
        for user in self.client_stdin.keys():
            # Check for Checksum Test
            join_msgs_count = 0
            # Check max transmission
            is_max_passed = list(map(lambda x: self.packets_[user].count(x) > util.NUM_OF_RETRANSMISSIONS+1, self.packets_[user]))
            if "True" in is_max_passed:
                print("Test Failed! A packet is retransmitted more than util.NUM_OF_RETRANSMISSIONS")
                return
            
            max_sent = 0
            seq_pkt = []
            max_ack = 0
            for pkt in self.packets_[user]:
                p_type, seq_no, data, checksum = util.parse_packet(pkt)
                seq_no = int(seq_no)
                if p_type == "start":
                    max_ack = 0
                if p_type == "ack":
                    seq_pkt = list(filter(lambda x: x >= max_ack, seq_pkt))
                    max_sent = max(max_sent, len(list(set(seq_pkt))) )
                    if max_sent > self.window:
                        print("Test Failed! More packets are in flight than window_size")
                        return
                    max_ack = max(seq_no, max_ack)
                    seq_pkt = list(filter(lambda x: x >= seq_no, seq_pkt))
                else:
                    seq_pkt.append(seq_no)
                    if p_type == "data" and user in data:
                        join_msgs_count += 1
            if max_sent < self.window:
                print("Test Failed! Less packets were sent than the available window")
                return
            if join_msgs_count < 3:
                print("Test Failed! Checksum Test Failed.")
        print("Test Passed!")
        return
    
    def handle_packet(self):
        for p,user in self.forwarder.in_queue:
            if len(p.full_packet) > 1500:
                self.packet_length_exceeded_limit += 1
                continue
            msg_type, a, b, c = util.parse_packet(p.full_packet.decode())
            if msg_type == "ack":
                if user in self.last_ack_dropped:
                    self.last_ack_dropped.remove(user)
                    self.packets_processed[msg_type] += 1
                    self.forwarder.out_queue.append((p,user))
                    self.packets_[user].append(p.full_packet.decode())
                else:
                    self.last_ack_dropped.append(user)
            else:
                if msg_type == "data" and self.checksum_test[user] == False:
                    p.full_packet = p.full_packet.decode() + "1"
                    p.full_packet = p.full_packet.encode()
                    self.packets_[user].append(p.full_packet.decode())
                    self.packets_processed[msg_type] += 1
                    self.checksum_test[user] = True
                    self.forwarder.out_queue.append((p,user))
                else:
                    self.packets_[user].append(p.full_packet.decode())
                    self.packets_processed[msg_type] += 1
                    self.forwarder.out_queue.append((p,user))
                
        # empty out the in_queue
        self.forwarder.in_queue = []