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
BROADCAST_PORT = 5000
BROADCAST_LISTENING_PORT = 5001
SERVER_GROUP = "224.1.1.1"
MULTICAST_PORT = 6000
MULTICAST_LISTENING_PORT = 6001
UNICAST_PORT = 7000
UNICAST_LISTENING_PORT = 7001
MY_PROCESS_ID = os.getpid()
MY_HOST = socket.gethostname()
MY_IP = socket.gethostbyname(MY_HOST)
SERVER_LIST={MY_PROCESS_ID:MY_IP}
CLIENT_LIST=[]
TIMEOUT = 5 # How long should the server wait for responses to initial broadcast? In seconds
TIMEOUT_SOCKET = 6 # How long until the socket times out when there are no responses? In seconds
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
                    print(prefixMessageWithDatetime("No response received from the broadcast group."))               
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
            print(prefixMessageWithDatetime(f"Received message from {addr}: {response}"))
            response_array = response.split("-")
            if response_array[0] not in SERVER_LIST:
                SERVER_LIST.update({int(response_array[0]):response_array[1]})

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
            print(prefixMessageWithDatetime(f"Received message from new leader, adress: {addr}, message: {response}"))
            LEADER_IP = response
        

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
            print(prefixMessageWithDatetime(f"Received message from {addr}: {response}"))
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
        LEADER_IP = MY_IP
        print(prefixMessageWithDatetime("Election finished. I'm the leader now. Informing others..."))   
        multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 10)     
        multicast_socket.sendto(MY_IP.encode(), (SERVER_GROUP, MULTICAST_PORT))    
    else:
        print(prefixMessageWithDatetime("Found Server with larger Process ID, passed on election."))        
        

###################################### Helpers ########################################

def broadcast(ip, port, broadcast_message):
    # Create a UDP socket
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Send message on broadcast address
    broadcast_socket.sendto(str.encode(broadcast_message), (ip, port))
    
def prefixMessageWithDatetime(message):
    # Add Current date and time to input message and return
    return datetime.now().strftime("%d.%m.%Y | %H:%M:%S")+" :: "+message
    
###################################### Main ##########################################

if __name__ == '__main__':
    
    # Starting server instance
    print(prefixMessageWithDatetime("Starting server instance..."))
    # Joining the broadcast group
    join_thread = threading.Thread(target=join())
   
    
    listener_thread = threading.Thread(target=broadcast_listen())
    
    join_thread.start()
    listener_thread.start()
    
    listener_thread = threading.Thread(target=multicast_listen())
    listener_thread.start()
    
    listener_thread = threading.Thread(target=unicast_listen())
    listener_thread.start()
    

    
    
    
    
    
    
    
    