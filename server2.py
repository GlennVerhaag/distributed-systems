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

#################################### Variables #######################################

# Calculate broadcast IP here: https://jodies.de/ipcalc using your IPv4 Address and subnet mask (run "ipconfig" on windows to get adress and mask)
BROADCAST_IP = "134.103.111.255"
BROADCAST_PORT = 5001
BROADCAST_LISTENING_PORT = 5000
MY_PROCESS_ID = os.getpid()
MY_HOST = socket.gethostname()
MY_IP = socket.gethostbyname(MY_HOST)
SERVER_LIST={MY_PROCESS_ID:MY_IP}
CLIENT_LIST=[]
TIMEOUT = 10 # How long should the server wait for responses to initial broadcast? In seconds
TIMEOUT_SOCKET = 6 # How long until the socket times out when there are no responses? In seconds
LEADER_IP = ""

#################################### Functions #######################################

def broadcast(ip, port, broadcast_message):
    # Create a UDP socket
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Send message on broadcast address
    broadcast_socket.sendto(str.encode(broadcast_message), (ip, port))
    
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
                    SERVER_LIST.update({response_array[0]:response_array[1]})
        except socket.timeout:
                    print(prefixMessageWithDatetime("No response received from the broadcast group, electing myself as leader!"))
                    # TODO: Leader election (self-election)
                    break             
    # TODO: Leader election             
    print(prefixMessageWithDatetime("Updated Server list (process ID : IP adress): " + str(SERVER_LIST)))    
    listen_socket.close()           
    
def listen(ip, port): # TODO: Maybe delete/rewrite this function, not sure yet 
    # Create a UDP socket
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket to broadcast and enable reusing addresses
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind socket to address and port
    listen_socket.bind((ip, port))
    
    print(prefixMessageWithDatetime("Listening to broadcast messages..."))
  
    while True:
        data, addr = listen_socket.recvfrom(1024)
        if data:
            print(prefixMessageWithDatetime(f"Received message from {addr}: {data.decode()}"))
       

def prefixMessageWithDatetime(message):
    # Add Current date and time to input message and return
    return datetime.now().strftime("%d.%m.%Y | %H:%M:%S")+" :: "+message
    
###################################### Main ##########################################

if __name__ == '__main__':
    
    # Starting server instance
    print(prefixMessageWithDatetime("Starting server instance..."))
    # Joining the broadcast group
    sender_thread = threading.Thread(target=join())
    sender_thread.start()
    

    
    
    
    
    
    
    
    