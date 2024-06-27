######################################################################################
#
# Authors: Jy Lai, Viktoria Wagner and Glenn Verhaag
# Sources: 
# - Slides, 04 Dynamic discovery.pdf
# - https://www.programiz.com/python-programming/datetime/current-datetime
# - https://www.geeksforgeeks.org/bully-algorithm-in-distributed-system/
#
#
######################################################################################

import socket
import threading
from datetime import datetime
import time
import os
import struct
import random
import pickle

#################################### Variables #######################################
#
# Setup socket to get own IP adress
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
#
# Calculate broadcast IP here: https://jodies.de/ipcalc using your IPv4 Address and subnet mask (run "ipconfig" on windows to get adress and mask)
BROADCAST_IP = "192.168.43.255"
BROADCAST_PORT = 5000
SERVER_GROUP = "224.1.1.1"
SERVER_HEARTBEAT_GROUP = "224.1.1.2"
MULTICAST_PORT = 6000
UNICAST_PORT = 7000
HEARTBEAT_PORT = 8000
NEW_CLIENT_PORT = 9000
CLIENT_MESSAGING_PORT = 10000
MY_PROCESS_ID = os.getpid()
MY_HOST = socket.gethostname()
MY_IP = s.getsockname()[0]
SERVER_LIST={MY_PROCESS_ID:MY_IP}
CLIENT_LIST=[]
TIMEOUT = 3 # How long should the server wait for responses to initial broadcast? In seconds
TIMEOUT_SOCKET = 3 # How long until the socket times out when there are no responses? In seconds
TIMEOUT_HEARTBEAT = 15
HEARTBEAT_INTERVALL = 1
LEADER_IP = ""
LEADER_PID = ""

#################################### Functions #######################################
 
def join():
    
    # Document the broadcast of own IP
    print(prefixMessageWithDatetime("Sending broadcast message with my IP ("+str(MY_IP)+") to the broadcast adress ("+str(BROADCAST_IP)+") on port "+str(BROADCAST_PORT)))
    # Broadcast own IP to broadcast adress
    broadcast(BROADCAST_IP, BROADCAST_PORT, str(MY_PROCESS_ID)+"-"+str(MY_IP))

    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    broadcast_socket.settimeout(TIMEOUT_SOCKET) # Socket timeout, if socket does not receive any message for x seconds it will stop listening
    broadcast_socket.bind((MY_IP, BROADCAST_PORT))
    # Bind socket to address and port
    
    '''
    Configure timeout for duration between messages. 
    Meaning that (after at least one message was already received and the socket timeout doesnt apply),
    if theres no further responses timeout applies.
    '''
    timeout = time.time()+TIMEOUT
    while True:
        print(prefixMessageWithDatetime("Listening for repsonses..."))
        
        if time.time() > timeout:
            break
        try:
            data, addr = broadcast_socket.recvfrom(1024)
            if data:
                print(prefixMessageWithDatetime(f"Received message from {addr}: {data.decode()}"))
                response = data.decode()
                response_array = response.split("-")
                if response_array[0] not in SERVER_LIST:
                    SERVER_LIST.update({int(response_array[0]):response_array[1]})
        except socket.timeout:
                    print(prefixMessageWithDatetime("Finished listening. No further responses."))               
                    break             
                
    print(prefixMessageWithDatetime("Updated Server list (process ID : IP adress): " + str(SERVER_LIST)))  
    # Start election after joining
    election()  
    broadcast_socket.close()
          
    
def broadcast_listen():  
    '''
    The broadcast listener is used to listen for new servers joining the server group.
    Listening for:
    - IP adress
    - Process ID
    of the new server.
    '''
    # Create a UDP socket
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket to broadcast and enable reusing addresses
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind socket to address range and port
    listen_socket.bind(("", BROADCAST_PORT))
    
    print(prefixMessageWithDatetime("Listening to broadcast messages on Port " + str(BROADCAST_PORT) + "..."))
    
    while True:
        data, addr = listen_socket.recvfrom(1024)
        
        if data:
            response = data.decode()
            response_array = response.split("-")
            if response_array[0] not in SERVER_LIST:
                print(prefixMessageWithDatetime(f"Received broadcast message from {addr}: {response}"))
                SERVER_LIST.update({int(response_array[0]):response_array[1]})
                print(prefixMessageWithDatetime(f"Updated my Server list: {SERVER_LIST}"))
                print(prefixMessageWithDatetime(f"Sending my IP ({MY_IP}) back to the new Server (IP: {response_array[1]}, ProcessID: {response_array[0]})"))
                broadcast(response_array[1], BROADCAST_PORT, str(MY_PROCESS_ID)+"-"+str(MY_IP))


def multicast_listen(): 
    '''
    The multicast listener is used to listen for leader announcments.
    Listening for:
    - IP adress OR Process ID (depends on the current implementation)
    of the new leader.
    '''
    # Create UDP multicast socket, bind it to multicast group and port
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(("",MULTICAST_PORT))
    membership = struct.pack("4sl", socket.inet_aton(SERVER_GROUP), socket.INADDR_ANY)
    listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
    
    print(prefixMessageWithDatetime("Listening to multicast messages on Port " + str(MULTICAST_PORT) + "..."))
    
    while True:
        
        data, addr = listen_socket.recvfrom(1024)
        if data: # Received message from new leader
            response = data.decode()
            response_array = response.split("-")
            if int(response_array[1]) != MY_PROCESS_ID: # Filter out own messages
                global LEADER_IP
                global LEADER_PID
                LEADER_IP = response_array[0]
                LEADER_PID = response_array[1]
                print(prefixMessageWithDatetime(f"Received message from new leader, adress: {addr}, message: {response}"))
                

def unicast_listen():
    '''
    The unicast listener is used to listen for messages prompting an election.
    Listening for:
    - Message directed to us, informing us to start our own election
    '''
    # Create a UDP socket
    unicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket to broadcast and enable reusing addresses
    unicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    unicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)                  
    unicast_socket.bind((MY_IP, UNICAST_PORT))
    
    print(prefixMessageWithDatetime("Listening to unicast messages on Port " + str(UNICAST_PORT) + "..."))
    
    while True:
        data, addr = unicast_socket.recvfrom(1024)
        if data:
            response = data.decode()
            if MY_PROCESS_ID != int(response): # Filter out election messages sent by us
                print(prefixMessageWithDatetime(f"Received unicast message from {addr}: {response}"))
                election()
          
def election(): 
    '''
    How the election works:
    1. Iterate through all server in our server list
    2. Check for all servers with a process ID larger than ours
    3. If there is one with a larger PID, set foundLarger to True and send messages to those servers in order to pass on the election
    4. If there is no server with a larger PID, Elect myself as leader and send a multicast message to the server group to inform them of my election as leader 
    '''
    print(prefixMessageWithDatetime("Starting my election..."))
    foundLarger = False
    for key in SERVER_LIST: 
        if key > MY_PROCESS_ID:
            foundLarger = True
            unicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            unicast_socket.sendto(str.encode(str(MY_PROCESS_ID)), (SERVER_LIST[key], UNICAST_PORT))
    
    if foundLarger == False: # In case I am the leader
        global LEADER_IP
        global LEADER_PID
        LEADER_IP = MY_IP
        LEADER_PID = MY_PROCESS_ID
        print(prefixMessageWithDatetime("Election finished. I'm the leader now. Informing others..."))   
        multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 10)     
        time.sleep(3)   
        multicast_socket.sendto((str(MY_IP)+"-"+str(MY_PROCESS_ID)).encode(), (SERVER_GROUP, MULTICAST_PORT))    
    else:
        print(prefixMessageWithDatetime("Found Server with larger Process ID, passed on election."))        
        
def send_heartbeats():
    multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 10)     
    
    while True:
        time.sleep(5) # Send one heartbeat every 5 seconds
        print(prefixMessageWithDatetime("Sending heartbeat..."))
        multicast_socket.sendto((str(MY_PROCESS_ID)+"-"+str(MY_IP)+"-"+str(LEADER_IP)).encode(), (SERVER_HEARTBEAT_GROUP, HEARTBEAT_PORT))

def listen_for_heartbeats():
    '''
    How the heartbeat listener works:
    1. Set up UDP multicast listener socket and listen for incomming heartbeat messages
    2. If we receive a heartbeat, reset the timeout timer for the server which sent the message
    3. Update the 'timers' dict in every loop iteration, based on the current updated server list
    4. Reduce the timer for all servers from which we did not receive a message by 1
      -> Check if one the timers has already hit 0, in that case assume that the server crashed and remove it from our server list
    '''
    print(prefixMessageWithDatetime("Listening for heartbeats on Port: "+str(HEARTBEAT_PORT)+"..."))
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(("", HEARTBEAT_PORT))
    membership = struct.pack("4sl", socket.inet_aton(SERVER_HEARTBEAT_GROUP), socket.INADDR_ANY)
    listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
    listen_socket.settimeout(HEARTBEAT_INTERVALL)
    
    timers = {}
    global SERVER_LIST 
    while True:
        
        try:   
            data, addr = listen_socket.recvfrom(1024)
            if data:
                response = data.decode()
                response_array = response.split("-")
                incomming_process_id = int(response_array[0])
                incomming_ip = response_array[1]
                incomming_leader_ip = response_array[2]
                
                ''' Fault tolerance: Check if incomming heartbeart agrees with me on who is the leader. If not, trigger election'''
                if incomming_leader_ip != LEADER_IP:
                    election()
                
                if incomming_process_id != MY_PROCESS_ID: # Ignore our own heartbeats
                    print(prefixMessageWithDatetime(f"Received heartbeat from {incomming_ip}"))
                    timers[incomming_process_id] = TIMEOUT_HEARTBEAT
                    
        except socket.timeout: # Wait for a new message for 5 seconds. If there isnt one, continue with the loop and try again next iteration
            pass
                
        for i in list(timers.keys()): 
            
            ''' Fault tolerance: Check if all servers that send a heartbeat are in our server list. If not, add them.'''
            if i not in SERVER_LIST.keys(): 
                SERVER_LIST.update({incomming_process_id:incomming_ip})             
        
            timers[i]=timers[i]-1
            print(prefixMessageWithDatetime(f"Timers: {timers}"))
            if timers[i] == 0:
                print(prefixMessageWithDatetime(f"Not receiving heartbeats from Server: {i}. Removing from Server list...")) 
                SERVER_LIST.pop(i) 
                timers.pop(i)
                print(prefixMessageWithDatetime(f"Updated Server list: {SERVER_LIST}"))
                election()    
                
def listen_for_new_clients():
    # Create a UDP socket
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket to broadcast and enable reusing addresses
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind socket to address range and port
    listen_socket.bind(("", NEW_CLIENT_PORT))   
    listen_socket.settimeout(1)   
    
    while True:
        if MY_IP == LEADER_IP and LEADER_PID == MY_PROCESS_ID:
            try:
                data, addr = listen_socket.recvfrom(1024)
            
                if data:
                    response = pickle.loads(data)
                    global CLIENT_LIST
                    if response[1] != MY_PROCESS_ID and response[3] != 1: #response[1] not in CLIENT_LIST:
                        #CLIENT_LIST.append(response[1]) 
                        print(prefixMessageWithDatetime(f"New Client joined the chat. Username: "+ response[2]+ "| IP adress: "+ response[0]))
                        broadcast(BROADCAST_IP, NEW_CLIENT_PORT, pickle.dumps([MY_IP,MY_PROCESS_ID, "Server", 1]), True)
            except socket.timeout: 
                pass  
                        
def listen_for_client_messages():
    # Create a UDP socket
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket to broadcast and enable reusing addresses
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind socket to address range and port
    listen_socket.bind(("", CLIENT_MESSAGING_PORT))
    listen_socket.settimeout(1)

    while True:
        if MY_IP == LEADER_IP and LEADER_PID == MY_PROCESS_ID:   
            try:
                data, addr = listen_socket.recvfrom(1024)
                if data:
                    response = pickle.loads(data)
                    
                    if response[1] != MY_PROCESS_ID and isinstance(response[2], int) != True and isinstance(response[3], int) != True:
                        print(prefixMessageWithDatetime("Received chat message, forwording to chat group."))
                        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        broadcast_socket.sendto(pickle.dumps([MY_IP, MY_PROCESS_ID, response[0], response[1], response[2], response[3]]), (BROADCAST_IP, CLIENT_MESSAGING_PORT))
            except socket.timeout: 
                pass                    

###################################### Helpers ########################################

def broadcast(ip, port, broadcast_message, already_encoded = False):
    # Create a UDP socket
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Send message on broadcast address
    if already_encoded == False:
        broadcast_socket.sendto(str.encode(broadcast_message), (ip, port))
    else:
        broadcast_socket.sendto(broadcast_message, (ip, port))
    broadcast_socket.close()
    
def prefixMessageWithDatetime(message):
    # Add Current date and time to input message and return
    return datetime.now().strftime("%H:%M:%S")+" :: "+ message
    
###################################### Main ##########################################

if __name__ == '__main__':
    
    # Starting server instance
    print(prefixMessageWithDatetime("Starting server instance..."))
    # Joining the broadcast group, wait until completed
    join_thread = threading.Thread(target=join)
    join_thread.start()
    join_thread.join()
    # Start listeners and heartbeat sender
    
    broadcast_listener_thread = threading.Thread(target=broadcast_listen)
    broadcast_listener_thread.start()
    
    multicast_listener_thread = threading.Thread(target=multicast_listen)
    multicast_listener_thread.start()
    
    unicast_listener_thread = threading.Thread(target=unicast_listen)
    unicast_listener_thread.start()
    
    heartbeat_sender_thread = threading.Thread(target=send_heartbeats)
    heartbeat_sender_thread.start()
    
    heartbeat_listener_thread = threading.Thread(target=listen_for_heartbeats)
    heartbeat_listener_thread.start()
    
    client_listener_thread = threading.Thread(target=listen_for_new_clients)
    client_listener_thread.start()
    
    message_listener_thread = threading.Thread(target=listen_for_client_messages)
    message_listener_thread.start()
    
    
    
    
    
    
    
    
    