import hashlib
import os
import random
from string import ascii_letters
import time
from testspart2 import BasicTest
import util

class OutOfOrderPacketsTest(BasicTest.BasicTest):
    def set_state(self):
        self.num_of_clients = 4
        self.client_stdin = {"client1": 1, "client2":2, "client3":3, "client4": 4}
        self.input = [  ("client1","list\n"),
                        ("client1","file 2 client1 client5 test_file2\n") ,
                     ]
        self.time_interval = 3
        self.num_of_acks = 8*2 + 2*2 +  2*2 
        with open("test_file2","w") as f:
            f.write(''.join(random.choice(ascii_letters) for i in range(10000)))
        self.last_time = time.time()
        self.handle_packet_time = self.last_time

    def result(self):
        self.result_basic()

    def handle_packet(self):
        if random.random() > 0.9:
            if time.time() - self.handle_packet_time > 0.1:
                for p,user in reversed(self.forwarder.in_queue):
                    if len(p.full_packet) > 1500:
                        self.packet_length_exceeded_limit += 1
                        continue
                    msg_type,a,b,c = util.parse_packet(p.full_packet.decode())

                    self.packets_processed[msg_type] += 1
                    self.forwarder.out_queue.append((p,user))

                # empty out the in_queue
                self.forwarder.in_queue = []
        else:
            for p,user in self.forwarder.in_queue:
                if len(p.full_packet) > 1500:
                    self.packet_length_exceeded_limit += 1
                    continue
                msg_type,a,b,c = util.parse_packet(p.full_packet.decode())

                self.packets_processed[msg_type] += 1
                self.forwarder.out_queue.append((p,user))

            # empty out the in_queue
            self.forwarder.in_queue = []
            self.handle_packet_time = time.time()
        self.handle_packet_time = time.time()