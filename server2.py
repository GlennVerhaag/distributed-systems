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

#################################### Variables #######################################

# Calculate broadcast IP here: https://jodies.de/ipcalc using your IPv4 Address and subnet mask (run "ipconfig" on windows to get adress and mask)
BROADCAST_IP = "172.25.191.255"
BROADCAST_PORT = 5001
BROADCAST_LISTENING_PORT = 5000
SERVER_GROUP = "224.1.1.1"
SERVER_HEARTBEAT_GROUP = "224.1.1.2"
MULTICAST_PORT = 6001
MULTICAST_LISTENING_PORT = 6000
UNICAST_PORT = 7001
UNICAST_LISTENING_PORT = 7000
HEARTBEAT_PORT = 8001
HEARTBEAT_LISTENING_PORT = 8000
MY_PROCESS_ID = os.getpid()
MY_HOST = socket.gethostname()
MY_IP = socket.gethostbyname(MY_HOST)
SERVER_LIST={MY_PROCESS_ID:MY_IP}
CLIENT_LIST=[]
TIMEOUT = 2 # How long should the server wait for responses to initial broadcast? In seconds
TIMEOUT_SOCKET = 2 # How long until the socket times out when there are no responses? In seconds
TIMEOUT_HEARTBEAT = 10
LEADER_IP = ""

#################################### Functions #######################################
 
def join():
    # Document the broadcast of own IP
    print(prefixMessageWithDatetime("Sending broadcast message with my IP ("+str(MY_IP)+") to the broadcast adress ("+str(BROADCAST_IP)+") on port "+str(BROADCAST_PORT)))
    # Broadcast own IP to broadcast adress
    broadcast(BROADCAST_IP, BROADCAST_PORT, str(MY_PROCESS_ID)+"-"+str(MY_IP))

    # Create a UDP socket for listening
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket to broadcast and enable reusing addresses
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.settimeout(TIMEOUT)
    
    # Bind socket to address and port
    listen_socket.bind((MY_IP, BROADCAST_LISTENING_PORT))
    # Check for response n (REQUEST_TIMEOUT) amount of times. If there is no response, assume that there is no other server in the broadcast group yet.
    timer=0
    timeout = time.time()+TIMEOUT
    while True:
        print(prefixMessageWithDatetime("Listening for repsonses..."))
        
        if time.time() > timeout:
            break
        try:
            data, addr = listen_socket.recvfrom(1024)
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
    election()  
    listen_socket.close()           
    
def broadcast_listen():  
    # Create a UDP socket
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket to broadcast and enable reusing addresses
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # Bind socket to address and port
    listen_socket.bind(("", BROADCAST_LISTENING_PORT))
    
    print(prefixMessageWithDatetime("Listening to broadcast messages on Port " + str(BROADCAST_LISTENING_PORT) + "..."))
    
    while True:
        data, addr = listen_socket.recvfrom(1024)
        
        if data:
            response = data.decode()
            print(prefixMessageWithDatetime(f"Received broadcast message from {addr}: {response}"))
            response_array = response.split("-")
            if response_array[0] not in SERVER_LIST:
                SERVER_LIST.update({int(response_array[0]):response_array[1]})
                print(prefixMessageWithDatetime(f"Updated my Server list: {SERVER_LIST}"))
                print(prefixMessageWithDatetime(f"Sending my IP ({MY_IP}) back to the new Server (IP: {response_array[1]}, ProcessID: {response_array[0]})"))
                broadcast(response_array[1], BROADCAST_PORT, str(MY_PROCESS_ID)+"-"+str(MY_IP))


def multicast_listen(): 
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(("",MULTICAST_LISTENING_PORT))
    
    membership = struct.pack("4sl", socket.inet_aton(SERVER_GROUP), socket.INADDR_ANY)
    
    listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
    
    print(prefixMessageWithDatetime("Listening to multicast messages on Port " + str(MULTICAST_LISTENING_PORT) + "..."))
    
    while True:
        
        data, addr = listen_socket.recvfrom(1024)
        if data:
            response = data.decode()
            LEADER_IP = response
            print(prefixMessageWithDatetime(f"Received message from new leader, adress: {addr}, message: {response}"))
                

def unicast_listen():
    # Create a UDP socket
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket to broadcast and enable reusing addresses
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)                 
    listen_socket.bind(("", UNICAST_LISTENING_PORT))
    
    print(prefixMessageWithDatetime("Listening to unicast messages on Port " + str(UNICAST_LISTENING_PORT) + "..."))
    
    while True:
        data, addr = listen_socket.recvfrom(1024)
        if data:
            response = data.decode()
            print(prefixMessageWithDatetime(f"Received multicast message from {addr}: {response}"))
            print(prefixMessageWithDatetime(f"Starting my election..."))
            election()
          
def election(): 
    print(prefixMessageWithDatetime("Starting election..."))
    foundLarger = False
    for key in SERVER_LIST:
        if key > MY_PROCESS_ID:
            foundLarger = True
            unicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            unicast_socket.sendto(str.encode("Start your election!"), (SERVER_LIST[key], UNICAST_PORT))
    
    if foundLarger == False:
        global LEADER_IP
        LEADER_IP = MY_IP
        print(prefixMessageWithDatetime("Election finished. I'm the leader now. Informing others..."))   
        multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 10)     
        time.sleep(2)   
        multicast_socket.sendto(MY_IP.encode(), (SERVER_GROUP, MULTICAST_PORT))    
    else:
        print(prefixMessageWithDatetime("Found Server with larger Process ID, passed on election."))        
        
def send_heartbeats():
    multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 10)     
    
    while True:
        time.sleep(1)   
        print("sending...")
        multicast_socket.sendto(str(MY_PROCESS_ID).encode(), (SERVER_HEARTBEAT_GROUP, HEARTBEAT_PORT))

def listen_for_heartbeats():
    print("Listening for heartbeats...")
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(("", HEARTBEAT_LISTENING_PORT))
    membership = struct.pack("4sl", socket.inet_aton(SERVER_HEARTBEAT_GROUP), socket.INADDR_ANY)
    listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
    listen_socket.settimeout(1)
    
    timers = {}
    
    while True:
        
        try:   
            data, addr = listen_socket.recvfrom(1024)
            if data:
                response = int(data.decode())
                print(f"received...{response}")
                timers[response] = TIMEOUT_HEARTBEAT
        except socket.timeout:
            pass
        
        for i in list(SERVER_LIST.keys()):
            if i != MY_PROCESS_ID and i not in timers: 
                timers.update({i:TIMEOUT_HEARTBEAT})
                
        for i in list(timers.keys()):
            print(i)
            timers[i]=timers[i]-1
            print(f"i: {i}  timers: {timers}")
            if timers[i] == 0:
                print(prefixMessageWithDatetime(f"Not receiving heartbeats from Server: {i}. Removing from Server list...")) 
                SERVER_LIST.pop(i) 
                timers.pop(i)
                print(prefixMessageWithDatetime(f"Updated Server list: {SERVER_LIST}"))
                print(LEADER_IP)
                if MY_IP != LEADER_IP:
                    election()      

###################################### Helpers ########################################

def broadcast(ip, port, broadcast_message):
    # Create a UDP socket
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Send message on broadcast address
    broadcast_socket.sendto(str.encode(broadcast_message), (ip, port))
    
def prefixMessageWithDatetime(message):
    # Add Current date and time to input message and return
    return datetime.now().strftime("%d.%m.%Y | %H:%M:%S")+" :: "+ message
    
###################################### Main ##########################################

if __name__ == '__main__':
    
    # Starting server instance
    print(prefixMessageWithDatetime("Starting server instance..."))
    # Joining the broadcast group
    join_thread = threading.Thread(target=join)
    join_thread.start()
    join_thread.join()
    listener_thread = threading.Thread(target=broadcast_listen)
    listener_thread.start()
    
    multicast_listener_thread = threading.Thread(target=multicast_listen)
    multicast_listener_thread.start()
    
    unicast_listener_thread = threading.Thread(target=unicast_listen)
    unicast_listener_thread.start()
    
    heartbeat_sender_thread = threading.Thread(target=send_heartbeats)
    heartbeat_sender_thread.start()
    
    heartbeat_listener_thread = threading.Thread(target=listen_for_heartbeats)
    heartbeat_listener_thread.start()
    
    
    