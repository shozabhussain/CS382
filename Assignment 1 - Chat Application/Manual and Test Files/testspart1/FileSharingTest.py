import random
from string import ascii_letters
from .BasicTest import *

class FileSharingTest(BasicTest):
    
    def set_state(self):
        self.num_of_clients = 3
        self.client_stdin = {"client1": 1, "client2":2, "client3":3}
        self.input = [  ("client1","list\n"),
                        ("client1","file 1 client2 test_file1\n"),
                        ("client3","file 3 client1 client2 client3 test_file2\n") ]
        self.last_time = time.time()

        with open("test_file1","w") as f:
            f.write(''.join(random.choice(ascii_letters) for i in range(2000)))
        
        with open("test_file2","w") as f:
            f.write(''.join(random.choice(ascii_letters) for i in range(3000)))

    def result(self):
        # Check if Output File Exists
        if not os.path.exists("server_out"):
            raise ValueError("No such file server_out")
        
        for client in self.client_stdin.keys():
            if not os.path.exists("client_"+client):
                raise ValueError("No such file %s"% "client_" + client)
        
        server_out = []
        clients_out = {}
        files = {"test_file1":[], "test_file2":[]}
        # Checking Join
        for client in self.client_stdin.keys():
            server_out.append("join: %s" % client)
            clients_out[client] = ["quitting"]
            server_out.append('disconnected: %s'% client)

        # Checking Output of Client Messages
        for inp in self.input_to_check:
            client,message = inp
            msg = message.split()
            if msg[0] == "list":
                server_out.append("request_users_list: %s" % client)
                clients_out[client].append("list: %s" % " ".join(sorted(self.client_stdin.keys())))
            elif msg[0] == "msg":
                server_out.append("msg: %s" % client)
                for i in range(int(msg[1])):
                    clients_out[msg[i + 2]].append("msg: %s: %s" % (client, " ".join(msg[2 + int(msg[1]):])) )
            elif msg[0] == "file":
                server_out.append("file: %s" % client)
                for i in range(int(msg[1])):
                    clients_out[msg[i + 2]].append("file: %s: %s" % (client, msg[2 + int(msg[1])]) )
                    files[msg[2+int(msg[1])]].append("%s_%s" % (msg[i+2],msg[2+int(msg[1])]))
        
        # Checking Clients Output
        for client in clients_out.keys():
            with open("client_"+client) as f:
                lines = f.read().split('\n')
                for each_line in clients_out[client]:
                    if each_line not in lines:
                        print("Test Failed: Client output is not correct",each_line)
                        return False

        # Checking Sever Output in File
        with open("server_out") as f:
            lines = f.read().split("\n")
            for each_line in server_out:
                if each_line not in lines:
                    print("Test Failed: Server Output is not correct")
                    return False
        
        # Checking Files
        for filename in files:
            for each_file in files[filename]:
                if not self.files_are_the_same(each_file, filename):
                    print("Test Failed: File is corrupted/not found")
                    return False
        print("Test Passed")
        return True