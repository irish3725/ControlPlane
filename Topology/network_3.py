import queue
import threading
import json
import sys 

 
## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)
    
    ##get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None
        
    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)
            
        
## Implements a network layer packet.
class NetworkPacket:
    ## packet encoding lengths 
    dst_S_length = 5
    prot_S_length = 1
    
    ##@param dst: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst, prot_S, data_S):
        self.dst = dst
        self.data_S = data_S
        self.prot_S = prot_S
        
    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()
        
    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise('%s: unknown prot_S option: %s' %(self, self.prot_S))
        byte_S += self.data_S
        return byte_S
    
    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0 : NetworkPacket.dst_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.dst_S_length : NetworkPacket.dst_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise('%s: unknown prot_S field: %s' %(self, prot_S))
        data_S = byte_S[NetworkPacket.dst_S_length + NetworkPacket.prot_S_length : ]        
        return self(dst, prot_S, data_S)
    

    

## Implements a network host for receiving and transmitting data
class Host:
    
    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False #for thread termination
    
    ## called when printing the object
    def __str__(self):
        return self.addr
       
    ## create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst, data_S):
        p = NetworkPacket(dst, 'data', data_S)
###        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out') #send packets always enqueued successfully
        
    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
###            print('%s: received packet "%s"' % (self, pkt_S))
            p = NetworkPacket.from_byte_S(pkt_S)
            if p.prot_S == 'data' and self.addr == 'H2':
                self.udt_send('H1', 'Return message to H1')          
             
    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return
        


## Implements a multi-interface router
class Router:
    
    ##@param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.destinations = ['H1', 'H2', 'H3', 'RA', 'RB', 'RC', 'RD']
        self.routers = ['RA', 'RB', 'RC', 'RD'] 
        self.stop = False #for thread termination
        self.name = name 
        #create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        #save neighbors and interfeces on which we connect to them
        self.cost_D = cost_D    # {neighbor: {interface: cost}}
        self.rt_tbl_D = {}      # {destination: {router: cost}}
        self.neighbor_L = [-1] * len(self.intf_L) 
        # initialize routing table 
        for router in self.routers:
            # add router entry to neighbor_L if it exists
            for neighbor, entry in self.cost_D.items():
                for interface in entry.keys(): 
                    self.neighbor_L[interface] = neighbor 
            # add empty dict as entry for all routers 
            self.rt_tbl_D[router] = {} 
            if router is self.name: 
                # add cost table for this router as an entry
                # in routing table for this router 
                self.rt_tbl_D[self.name] = self.cost_D
        print('%s: Initialized routing table' % self)
        self.print_routes()


    ## called when printing the object
    def __str__(self):
        return self.name


    ## look through the content of incoming interfaces and 
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            #get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            #if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p,i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))
            

    ## forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        try:
            # get destination
            dst = p.dst 
            # get out interface from routing table
            for interface, cost in self.rt_tbl_D[self.name][dst].items():
                # for now we assume the outgoing interface is 1
                self.intf_L[interface].put(p.to_byte_S(), 'out', True)
###                print('%s: forwarding packet "%s" from interface %d to %d' % \
###                    (self, p, i, interface))
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self, i):
        # turn table into a string 
        rt_tbl_S = json.dumps(self.rt_tbl_D) 
        #create a routing table update packet
        p = NetworkPacket(0, 'control', rt_tbl_S)
        try:
###            print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        # booleans to tell if we need to update our neighbors
        update = False 
      
        update_D = json.loads(p.data_S)
        for router, entry in update_D.items():
            # if entry is not referring to this router
            if router != self.name:           
                # update the entry 
                self.rt_tbl_D[router] = entry      

        update = self.update_table(i) 
        # print new routing table 
        self.print_routes()
        # if we got a new entry or updated our table  
        if update:
            # send routes out all interfaces 
            for i in range(len(self.intf_L)):
                self.send_routes(i)

    ## Use Bellman-Ford to update table
    def update_table(self, in_interface):
        # boolean for if we need to update our neighbors
        update = False

        distance, predecessor = self.Bellman_Ford()
      
        # input new row into routing table
        for dst in self.destinations:
            # get index in distance of this destination 
            i = self.destinations.index(dst) 
            # check to see if there is already an entry 
            if dst in self.rt_tbl_D[self.name].keys(): 
                for interface, cost in self.rt_tbl_D[self.name][dst].items():
                    # if cost is now different, get new interface
                    # and input new cost 
                    if cost < distance[i]:
                        nInterface = self.get_interface(dst, predecessor) 
                        # check to see if we have valid new interface
                        if nInterface == -1:
                            nInterface = interface
 
                        self.rt_tbl_D[self.name][dst] = {nInterface: distance[i]}
                        update = True  
            # if there is no entry, create one
            else:
                nInterface = self.get_interface(dst, predecessor) 
                self.rt_tbl_D[self.name][dst] = {nInterface: distance[i]}
                update = True                

 
        return update
  
    def get_interface(self, destination, predecessor):
        for i in range(len(predecessor)): 
            # check to see if destination is self
            destination_index = self.destinations.index(destination) 
            if destination == self.name or predecessor[destination_index] == None:
                return -1 
            # if we find the destination in self.neighbor_L, 
            # return that interface
            if destination in self.neighbor_L:
                return self.neighbor_L.index(destination)
            else:
                destination = self.destinations.index(destination)
###                print('destination index:', destination) 
                destination = predecessor[destination] 
###                print('predecessor index:', destination) 
###                print('predecessor list:', predecessor) 
                destination = self.destinations[destination] 
        return -1        

    def Bellman_Ford(self):
        edges = list()
        # for each router, find all edges connected to that router 
        for router in self.routers:
            # for each possible destination 
            for dst in self.destinations:
                # if destination is connected to router 
                if dst in self.rt_tbl_D[router].keys():
                    # add edge to list
                    for interface, cost in self.rt_tbl_D[router][dst].items():
                        edges.append([router, dst, cost]) 

        # create list of distances to calculate
        # and fill with inf values
        distance = [sys.maxsize] * len(self.destinations) 

        # create list of predecessors
        predecessor = [None] * len(self.destinations)

        # set distance to self to 0
        distance[self.destinations.index(self.name)] = 0

        # iterate number of edges - 1 times
        for i in range(len(edges) - 1):
            # for each edge we see, do comparisons 
            for edge in edges:
                # get vertices u, v from edge 
                u = self.destinations.index(edge[0])
                v = self.destinations.index(edge[1])
        
                # if we find a shorter path, change distance 
                # do this twice because edges are bi-directional
                if (distance[u] + edge[2]) < distance[v]:
                    distance[v] = distance[u] + edge[2]
                    predecessor[v] = u 
#                if (distance[v] + edge[2]) < distance[u]:
#                    distance[u] = distance[v] + edge[2]
#                    predecessor[v] = u 

        return distance, predecessor 
 
    ## Print routing table
    def print_routes(self):
        if self.name != 'RA':
            return 
        print('\nRouting Table for %s:' % (self.name))
        print('\n             Cost To')
        print('             ', end='')
        # print all possible destinations 
        for dst in self.destinations:
            print(dst, end='  ') 
        # get each row (key) from routing table 
        for key in self.rt_tbl_D.keys():
            print()
            # give the table some space with prefix 
            prefix = '        ' 
            # if the row is middleish, write From 
            if key == 'RA': 
                prefix = ' From   '     
            print(prefix, key, end = '   ') 
            # now in same order as above, print costs within row 
            for dst in self.destinations:
                # if there is an entry for this destination
                if dst in self.rt_tbl_D[key].keys(): 
                    # start final_cost as large value 
                    final_cost = sys.maxsize 
                    # check all interfaces for cost 
                    for interface, cost in self.rt_tbl_D[key][dst].items(): 
                        # if this interface has lowest cost, set as final 
                        if cost < final_cost:
                            final_cost = cost 
                    # print lowest cost to destination print(final_cost, end = '   ') 
                    if final_cost == sys.maxsize:
                        print('~', end='   ')     
                    else:
                        print(final_cost, end='   ')     
                    #print(self.rt_tbl_D[key][dst], end='')
                else:
                    print('~', end='   ') 
        print('\n')

                
    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return 
