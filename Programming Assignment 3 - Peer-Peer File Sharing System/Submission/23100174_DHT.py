import socket
import threading
import os
import time
import hashlib
from json import dumps, loads
import pickle


class Node:
	def __init__(self, host, port):
		self.stop = False
		self.host = host
		self.port = port
		self.M = 16
		self.N = 2**self.M
		self.key = self.hasher(host+str(port))
		# You will need to kill this thread when leaving, to do so just set self.stop = True
		threading.Thread(target = self.listener).start()
		self.files = []
		self.backUpFiles = []
		if not os.path.exists(host+"_"+str(port)):
			os.mkdir(host+"_"+str(port))
		'''
		------------------------------------------------------------------------------------
		DO NOT EDIT ANYTHING ABOVE THIS LINE
		'''
		# Set value of the following variables appropriately to pass Intialization test
		self.successor = (self.host, self.port)
		self.predecessor = (self.host, self.port)
		self.suc_of_suc = (self.host, self.port)
		self.ping = True
		# additional state variables

	def send_recv_msg(self, soc_recver, msg):
		'''
		Function to take in msg from node and send it and receive it appropriately
		'''
		soc = socket.socket()
		soc.connect( soc_recver )
		content = pickle.dumps(msg)
		soc.send(content)

		# when get function is called on the node ------------------------------------------------------------------------------------------
		if(msg[0] == "get_file"):
			msg_recv = soc.recv(1024)
			msg_recv = pickle.loads(msg_recv)

			if msg_recv == "file_found":
				time.sleep(0.5)
				self.recieveFile(soc, msg[1])
				soc.close()
				return msg[1]

			elif msg_recv == "file_not_found":
				soc.close()
				return None

		# when put function is called on the node ----------------------------------------------------------------------------------------------
		if(msg[0] == "put_file"):
			time.sleep(0.5)
			self.sendFile(soc, msg[1])
			soc.close()
			return

		# types of messages where you just want to send a message and expect no reply ------------------------------------------------------------
		if(msg[0] == "update_suc" or msg[0] == "leaving" or msg[0] == "my_new_files" or msg[0] == "i_am_your_pred" or msg[0] == "sos_node_dead"):
			soc.close()
			return

		# types of messages where you want to send a message and expect a reply in return ---------------------------------------------------------
		else:
			msg_recv = soc.recv(1024)
			msg_recv = pickle.loads(msg_recv)
			soc.close()
			return msg_recv



	def lookup(self, lookup_key):

		suc_hash_key = self.hasher( (self.successor[0] + str(self.successor[1]) ) )

		# corner case 1 ----------------------------------------------------------------------------------------------------------------
		if(self.key == suc_hash_key):
			return self.successor

		# general case ------------------------------------------------------------------------------------------------------------------
		elif(self.key < suc_hash_key):

			if(lookup_key <= suc_hash_key and lookup_key > self.key):
				return self.successor

			else:
				return self.send_recv_msg(self.successor, ("lookup", lookup_key) )

		# if you are the greatest key in the ring ----------------------------------------------------------------------------------------
		elif(self.key > suc_hash_key):

			if(lookup_key > suc_hash_key and lookup_key < self.key):
				return self.send_recv_msg(self.successor, ("lookup", lookup_key) )

			else:
				return self.successor


	def hasher(self, key):
		'''
		DO NOT EDIT THIS FUNCTION.
		You can use this function as follow:
			For a node: self.hasher(node.host+str(node.port))
			For a file: self.hasher(file)
		'''
		return int(hashlib.md5(key.encode()).hexdigest(), 16) % self.N


	def handleConnection(self, client, addr):
		'''
		 Function to handle each inbound connection, called as a thread from the listener.
		'''

		content = client.recv(1024)
		msg_type, msg = pickle.loads(content)

		if msg_type == "lookup":
			node_to_send = self.lookup(msg)
			node_to_send = pickle.dumps(node_to_send)
			client.send(node_to_send)

		# sending back my predec --------------------------------------------------------------------------------------------------------
		elif msg_type == "am_i_your_pred":
			node_to_send = pickle.dumps(self.predecessor)
			client.send(node_to_send)

		# updating my predec -------------------------------------------------------------------------------------------------------------
		elif msg_type == "i_am_your_pred":
			self.predecessor = msg

		# updating my succ ----------------------------------------------------------------------------------------------------------------
		elif msg_type == "update_suc":
			self.successor = msg
			self.send_recv_msg( self.successor, ("i_am_your_pred", (self.host, self.port) ) )  # notifying my new succ, that i am its new predec
			self.suc_of_suc = self.send_recv_msg( self.successor, ("need_succ", "") ) # getting its succ to update my succ of succ

		# you receiving a new file that has been hashed to you ----------------------------------------------------------------------------
		elif msg_type == "put_file":
			self.files.append(msg)

			self.send_recv_msg( self.successor, ("my_new_files", self.files ) ) # send updated files list to succ so it can update its backup for your files

			path = self.host + '_' + str(self.port) + "/" + msg
			time.sleep(1)
			self.recieveFile(client, path)

		# you sending file hashed to you, when get query has been called ----------------------------------------------------------------------
		elif msg_type == "get_file":

			if msg in self.files:
				client.send(pickle.dumps("file_found"))
				path = self.host + '_' + str(self.port) + "/" + msg
				time.sleep(5)
				self.sendFile(client, path)

			else:
				client.send(pickle.dumps("file_not_found"))

		# a new node asking for their share of files ---------------------------------------------------------------------------------------------
		elif msg_type == "give_my_files":

			list_to_send = []

			for i in self.files:

				if (self.key > msg): 			# general case when i am greater than my predec

					if (self.hasher(i) <= msg) :

						list_to_send.append(i)

				elif (self.key < msg ): 		# corner case when my predec is greater than me

					if (self.hasher(i) <= msg) and (self.hasher(i) > self.key):

						list_to_send.append(i)

			self.backUpFiles = list_to_send

			for i in self.backUpFiles: 			# removes files from main list and transfer to backup list

				if i in self.files:
					self.files.remove(i)

			client.send( pickle.dumps(list_to_send) )
			self.send_recv_msg( self.successor, ("my_new_files", self.files ) ) 	# notify my succ about my new files list so it can update its backup

		# when your predec is leaving, you tranfer its files from backup to main files list ----------------------------------------------------------
		elif msg_type == "leaving":
			self.files.extend(msg[0])
			self.backUpFiles = msg[1]
			self.send_recv_msg( self.successor, ("my_new_files", self.files ) ) # updating your succ about your new files so it could update its backup

		# send back your predec ----------------------------------------------------------------------------------------------------------------------
		elif msg_type == "need_succ":
			node_to_send = pickle.dumps(self.successor)
			client.send(node_to_send)

		# when your predec is dead, you tranfer its files from backup to main files list -------------------------------------------------------------
		elif msg_type == "sos_node_dead":
			self.files.extend(self.backUpFiles)
			self.send_recv_msg( self.successor, ("my_new_files", self.files ) )

		# updating backup for predec's files when its files are updated ------------------------------------------------------------------------------
		elif msg_type == "my_new_files":
			self.backUpFiles = msg

	def listener(self):
		'''
		We have already created a listener for you, any connection made by other nodes will be accepted here.
		For every inbound connection we spin a new thread in the form of handleConnection function. You do not need
		to edit this function. If needed you can edit signature of handleConnection function, but nothing more.
		'''
		listener = socket.socket()
		listener.bind((self.host, self.port))
		listener.listen(10)
		while not self.stop:
			client, addr = listener.accept()
			threading.Thread(target = self.handleConnection, args = (client, addr)).start()
		print ("Shutting down node:", self.host, self.port)
		try:
			listener.shutdown(2)
			listener.close()
		except:
			listener.close()


	def pinging(self):
		'''
		Function to ping its succ after every 0.5 secs and detect and take actions when its succ fails ----------------------------------------------
		'''
		while not self.stop:

			counter = 0
			content = pickle.dumps( ("am_i_your_pred", "") )

			while(counter < 3 and not self.stop):

				try:
					soc = socket.socket()
					soc.settimeout(0.1)
					soc.connect( self.successor )
					soc.send(content)
					msg = soc.recv(1024)
					msg = pickle.loads(msg)

					if msg != ( (self.host, self.port) ): # i am no longer my succ's predec because a new node has joined in between us
						soc.close()
						self.successor = msg # updating my succ to that new node
						self.send_recv_msg( self.successor, ("i_am_your_pred", (self.host, self.port) ) ) # notifying my new succ that i its new predec

					counter = 0
				except:
					counter = counter + 1

				time.sleep(0.5)

			if self.stop:
				soc.close()
				return

			else:
				soc.close()
				self.successor = self.suc_of_suc
				self.send_recv_msg( self.successor, ("i_am_your_pred", (self.host, self.port) ) )	# notifying my new succ that i its new predec
				self.suc_of_suc = self.send_recv_msg( self.successor, ("need_succ", "") ) 			# asking succ for its succ to update my succ of succ
				self.send_recv_msg( self.successor, ( "sos_node_dead", "" ) ) 				# notifying my new succ that its predec is dead so update files

	def join(self, joiningAddr):
		'''
		This function handles the logic of a node joining. This function should do a lot of things such as:
		Update successor, predecessor, getting files, back up files. SEE MANUAL FOR DETAILS.
		'''

		# general case -----------------------------------------------------------------------------------------------------------------------
		if joiningAddr != "":

			self.successor = self.send_recv_msg( joiningAddr, ("lookup", self.key) )
			self.files = self.send_recv_msg(self.successor, ("give_my_files", self.key) ) # getting my share of files

			if len(self.files) != 0:

				for i in self.files:
					time.sleep(0.5)
					self.get(i)

			self.send_recv_msg( self.successor, ("i_am_your_pred", (self.host, self.port) ) )	# notifying my new succ that i its new predec
			self.suc_of_suc = self.send_recv_msg( self.successor, ("need_succ", "") )			# asking succ for its succ to update my succ of succ

			threading.Thread(target = self.pinging ).start()

		# corner case 1 --------------------------------------------------------------------------------------------------------------------------
		else:
			threading.Thread(target = self.pinging ).start()


	def put(self, fileName):
		'''
		This function should first find node responsible for the file given by fileName, then send the file over the socket to that node
		Responsible node should then replicate the file on appropriate node. SEE MANUAL FOR DETAILS. Responsible node should save the files
		in directory given by host_port e.g. "localhost_20007/file.py".
		'''

		file_key = self.hasher(fileName)
		node_to_put = self.lookup(file_key)
		self.send_recv_msg(node_to_put, ("put_file", fileName) )


	def get(self, fileName):
		'''
		This function finds node responsible for file given by fileName, gets the file from responsible node, saves it in current directory
		i.e. "./file.py" and returns the name of file. If the file is not present on the network, return None.
		'''

		file_key = self.hasher(fileName)
		node_to_get = self.lookup(file_key)
		return self.send_recv_msg(node_to_get, ("get_file", fileName) )

	def leave(self):
		'''
		When called leave, a node should gracefully leave the network i.e. it should update its predecessor that it is leaving
		it should send its share of file to the new responsible node, close all the threads and leave. You can close listener thread
		by setting self.stop flag to True
		'''
		self.stop = True
		self.ping = False
		self.send_recv_msg( self.predecessor, ("update_suc", self.successor ) )
		self.send_recv_msg( self.successor, ("leaving", (self.files, self.backUpFiles) ) )



	def sendFile(self, soc, fileName):
		'''
		Utility function to send a file over a socket
			Arguments:	soc => a socket object
						fileName => file's name including its path e.g. NetCen/PA3/file.py
		'''
		fileSize = os.path.getsize(fileName)
		soc.send(str(fileSize).encode('utf-8'))
		soc.recv(1024).decode('utf-8')
		with open(fileName, "rb") as file:
			contentChunk = file.read(1024)
			while contentChunk!="".encode('utf-8'):
				soc.send(contentChunk)
				contentChunk = file.read(1024)

	def recieveFile(self, soc, fileName):
		'''
		Utility function to recieve a file over a socket
			Arguments:	soc => a socket object
						fileName => file's name including its path e.g. NetCen/PA3/file.py
		'''
		fileSize = int(soc.recv(1024).decode('utf-8'))
		soc.send("ok".encode('utf-8'))
		contentRecieved = 0
		file = open(fileName, "wb")
		while contentRecieved < fileSize:
			contentChunk = soc.recv(1024)
			contentRecieved += len(contentChunk)
			file.write(contentChunk)
		file.close()

	def kill(self):
		# DO NOT EDIT THIS, used for code testing
		self.stop = True


