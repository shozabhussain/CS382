import sys
from collections import defaultdict
from router import Router
from packet import Packet
from json import dumps, loads


class DVrouter(Router):
    """Distance vector routing protocol implementation."""

    def __init__(self, addr, heartbeatTime):
        """TODO: add your own class fields and initialization code here"""
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0

        # Hints: initialize local state

        self.nbrs = {}              # dict to store neighbors and their respective costs
        self.routing_table = {}
        self.neighbors = {}         # dict to store neighbors and their respective ports
        self.others_table = {}      # dict to store the routing tables of neighbors


    def handlePacket(self, port, packet):
        """TODO: process incoming packet"""
        if packet.isTraceroute():
            # Hints: this is a normal data packet
            # if the forwarding table contains packet.dstAddr
            #   send packet based on forwarding table, e.g., self.send(port, packet)

            if packet.dstAddr in self.routing_table.keys():

                self.send(self.routing_table[packet.dstAddr]["port"], packet)

        else:
            # Hints: this is a routing packet generated y your routing protocol
            # if the received distance vector is different
            #   update the local copy of the distance vector
            #   update the distance vector of this router
            #   update the forwarding table
            #   broadcast the distance vector of this router to neighbors

            table_recv = loads(packet.content)

            # stores the routing table of the nbr
            self.others_table[packet.srcAddr] = table_recv

            # searches if a node is deleted
            for x in table_recv.keys():
                if table_recv[x]["cost"] == 16:
                    deleted = x
                    self.remove_node(deleted)

            self.recompute_table()
            self.broadcast_handle_packet(packet.srcAddr, table_recv)

    def handleNewLink(self, port, endpoint, cost):
        """TODO: handle new link"""
        # update the distance vector of this router
        # update the forwarding table
        # broadcast the distance vector of this router to neighbors

        self.routing_table[endpoint] = {"cost":cost, "nextHop":endpoint, "port":port}
        self.neighbors[endpoint] = port
        self.nbrs[endpoint] = cost
        self.broadcast(endpoint)



    def handleRemoveLink(self, port):
        """TODO: handle removed link"""
        # update the distance vector of this router
        # update the forwarding table
        # broadcast the distance vector of this router to neighbors

        # finds the endpoint to be deleted through it's port
        endpoint_remove = list(self.neighbors.keys())[list(self.neighbors.values()).index(port)]
        self.routing_table[endpoint_remove]["cost"] = 16
        self.nbrs[endpoint_remove] = 16
        del self.neighbors[endpoint_remove]
        self.remove_node(endpoint_remove)
        self.recompute_table()
        self.broadcast(-16)


    def handleTime(self, timeMillisecs):
        """TODO: handle current time"""
        if timeMillisecs - self.last_time >= self.heartbeatTime:
            self.last_time = timeMillisecs

            # broadcast the distance vector of this router to neighbors
            self.broadcast(-16)


    def debugString(self):
        """TODO: generate a string for debugging in network visualizer"""
        return dumps(self.routing_table)


    def broadcast(self, node):

        packet_to_send = Packet(kind = Packet.ROUTING, srcAddr= self.addr, dstAddr= self.addr, content=dumps( self.routing_table ))

        for x in self.neighbors.keys():

            # if the node is same as the one from which the packet is recv then don't resend to it
            if x == node:
                continue
            else:
                self.send(self.neighbors[x], packet_to_send)


    def broadcast_handle_packet(self, node, table):

        packet_to_send = Packet(kind = Packet.ROUTING, srcAddr= self.addr, dstAddr= self.addr, content=dumps( self.routing_table ))

        for x in self.neighbors.keys():

            if x == node:
                continue

            # if the packet src and you have mutual nbrs then don't send because packet src has already send it to them
            elif x in table.keys():
                continue

            else:
                self.send(self.neighbors[x], packet_to_send)


    # node is the deleted link, function traverses table of each router and change this node's cost in each table to 16
    def remove_node(self, node):

        for x in self.others_table.keys():

            if node in self.others_table[x].keys():

                self.others_table[x][node]["cost"] = 16

    # reconstruct the table without the node which has been deleted
    def recompute_table(self):

        self.routing_table.clear()

        # inserting nbrs into table
        for x in self.nbrs.keys():

            if self.nbrs[x] == 16:
                continue

            self.routing_table[x] = {"cost":self.nbrs[x], "nextHop":x, "port":self.neighbors[x]}

        # inserting all other nodes in the table from stored tables of other routers
        for x, y in self.others_table.items():

            table_recv = y
            srcAddr = x

            if self.nbrs[x] == 16:
                continue

            for endpoint in table_recv.keys():

                if table_recv[endpoint]["cost"] == 16:
                    continue

                if endpoint == self.addr:
                    continue

                if endpoint not in self.routing_table.keys():

                    new_cost = self.nbrs[srcAddr] + table_recv[endpoint]["cost"]
                    hop =srcAddr
                    self.routing_table[endpoint] = {"cost":new_cost, "nextHop":hop, "port":self.neighbors[hop]}

                elif endpoint in self.routing_table.keys():

                    new_cost = self.nbrs[srcAddr] + table_recv[endpoint]["cost"]
                    hop = srcAddr

                    if self.routing_table[endpoint]["cost"] >= new_cost:
                        self.routing_table[endpoint] = {"cost":new_cost, "nextHop":hop, "port":self.neighbors[hop]}