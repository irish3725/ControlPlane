import network_3 as network
import link_3 as link
import threading
from time import sleep
import sys

##configuration parameters
router_queue_size = 0 #0 means unlimited
simulation_time = 10   #give the network sufficient time to execute transfers

if __name__ == '__main__':
    object_L = [] #keeps track of objects, so we can kill their threads at the end
    
    #create network hosts
    host_1 = network.Host('H1')
    object_L.append(host_1)
    host_2 = network.Host('H2')
    object_L.append(host_2)
    host_3 = network.Host('H3')
    object_L.append(host_3)
    
    #create routers and cost tables for reaching neighbors
    # table for RA 
    cost_D = {'H1': {0: 1}, 'H2': {1: 1}, 'RB': {2: 3}, 'RC': {3: 1}} # {neighbor: {interface: cost}}
    router_a = network.Router(name='RA', 
                              cost_D = cost_D,
                              max_queue_size=router_queue_size)
    object_L.append(router_a)

    # table for RB
    cost_D = {'RA': {0: 3}, 'RD': {1: 1}} # {neighbor: {interface: cost}}
    router_b = network.Router(name='RB', 
                              cost_D = cost_D,
                              max_queue_size=router_queue_size)
    object_L.append(router_b)

    # table for RC
    cost_D = {'RA': {0: 1}, 'RD': {1: 3}} # {neighbor: {interface: cost}}
    router_c = network.Router(name='RC', 
                              cost_D = cost_D,
                              max_queue_size=router_queue_size)
    object_L.append(router_c)

    # table for RD
    cost_D = {'RB': {0: 1}, 'RC': {1: 3}, 'H3': {2: 1}} # {neighbor: {interface: cost}}
    router_d = network.Router(name='RD', 
                              cost_D = cost_D,
                              max_queue_size=router_queue_size)
    object_L.append(router_d)
    
    #create a Link Layer to keep track of links between network nodes
    link_layer = link.LinkLayer()
    object_L.append(link_layer)
    
    #add all the links - need to reflect the connectivity in cost_D tables above
    link_layer.add_link(link.Link(host_1, 0, router_a, 0))
    link_layer.add_link(link.Link(host_2, 0, router_a, 1))
    link_layer.add_link(link.Link(router_a, 2, router_b, 0))
    link_layer.add_link(link.Link(router_a, 3, router_c, 0))
    link_layer.add_link(link.Link(router_b, 1, router_d, 0))
    link_layer.add_link(link.Link(router_c, 1, router_d, 1))
    link_layer.add_link(link.Link(router_d, 2, host_3, 0))
    
    
    #start all the objects
    thread_L = []
    for obj in object_L:
        thread_L.append(threading.Thread(name=obj.__str__(), target=obj.run)) 
    
    for t in thread_L:
        t.start()
    
    ## compute routing tables
    router_a.send_routes(3) #one update starts the routing process
    sleep(simulation_time)  #let the tables converge
    print("Converged routing tables")
    router_a.print_routes(True)
    router_b.print_routes(True)
    router_c.print_routes(True)
    router_d.print_routes(True)
    for obj in object_L:
        if str(type(obj)) == "<class 'network.Router'>":
            obj.print_routes(True)

    #send packet from host 1 to host 2
    host_1.udt_send('H3', 'MESSAGE_FROM_H1')
    sleep(simulation_time)
    
    
    #join all threads
    for o in object_L:
        o.stop = True
    for t in thread_L:
        t.join()
        
    print("All simulation threads joined")

