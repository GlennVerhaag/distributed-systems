######################################################################################
#
# Authors: Jy Lai, Viktoria Wagner and Glenn Verhaag
# Sources: 
# - 
#
######################################################################################

import socket
import threading
from datetime import datetime
import os
import sys
import pickle
from prompt_toolkit import PromptSession
session = PromptSession()
from prompt_toolkit.patch_stdout import patch_stdout

#################################### Variables #######################################
# Setup socket to get own IP adress
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
#
BROADCAST_IP = "192.168.43.255"
NEW_CLIENT_PORT = 9000
CLIENT_MESSAGING_PORT = 10000
TIMEOUT_INTERVALL = 1
 
MY_IP = s.getsockname()[0]
MY_PROCESS_ID = os.getpid()
LEADER_IP = ""
USERNAME = ""
LEADER_PID = ""

#################################### Functions #######################################

def join():
    global USERNAME
    USERNAME = input(prefixMessageWithDatetime("Username: "))
    print(prefixMessageWithDatetime("Hello "+USERNAME+"!"))
    print(prefixMessageWithDatetime("Joining the chatroom..."))
    
    send_join_message(USERNAME)
    sys.exit(0)
                
def send_chat_message():
    
    while True:
        # Create a UDP socket
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set the socket to broadcast and enable reusing addresses
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind socket to address range and port
        listen_socket.bind(("", CLIENT_MESSAGING_PORT))
        listen_socket.settimeout(TIMEOUT_INTERVALL)
        server_response = False
        with patch_stdout():
            message = session.prompt(prefixMessageWithDatetime(USERNAME+' > '))
            # message = input(prefixMessageWithDatetime("Message: "))
            broadcast(BROADCAST_IP, CLIENT_MESSAGING_PORT, pickle.dumps([MY_IP, MY_PROCESS_ID, message, USERNAME]) )
            print( "✔️", end="", flush=True)
            while True:
                try:
                    data, addr = listen_socket.recvfrom(1024)
                    if data : 
                        response = pickle.loads(data)
                        if response[1] != MY_PROCESS_ID and response[0] == LEADER_IP and response[1] == LEADER_PID:
                            server_response = True
                            print("✔️")
                            listen_socket.close()
                            break
                            
                except socket.timeout: 
                    listen_socket.close()
                    break            
            if server_response == False :   
                print("\n"+prefixMessageWithDatetime("Message could not be delivered. Reconnecting to Server..."))
                send_join_message(USERNAME)
                listen_socket.close()
                pass
            
def listen_for_messages():
    # Create a UDP socket
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket to broadcast and enable reusing addresses
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind socket to address range and port
    listen_socket.bind(("", CLIENT_MESSAGING_PORT))
    listen_socket.settimeout(TIMEOUT_INTERVALL)
                         
    while True:
        try:
            data, addr = listen_socket.recvfrom(1024)
            if data : 
                response = pickle.loads(data)
                if response[1] != MY_PROCESS_ID and response[3] != MY_PROCESS_ID:
                    if response[0] == LEADER_IP and response[1] == LEADER_PID:
                        print(prefixMessageWithDatetime(str(response[5]))+" > "+str(response[4]))
                    
        except socket.timeout: 
            pass            
###################################### Helpers ########################################

def broadcast(ip, port, broadcast_message):
    # Create a UDP socket
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Send message on broadcast address
    broadcast_socket.sendto(broadcast_message, (ip, port))
    broadcast_socket.close()
    
def prefixMessageWithDatetime(message):
    # Add Current date and time to input message and return
    return datetime.now().strftime("%H:%M:%S")+" :: "+ message    

def send_join_message(username):
    # Create a UDP socket
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket to broadcast and enable reusing addresses
    # listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind socket to address range and port
    listen_socket.bind((MY_IP, NEW_CLIENT_PORT)) 
    listen_socket.settimeout(TIMEOUT_INTERVALL)
    global LEADER_IP
    global LEADER_PID
    
    while True:
            broadcast(BROADCAST_IP, NEW_CLIENT_PORT, pickle.dumps([MY_IP,MY_PROCESS_ID, USERNAME, 0]))
            print(prefixMessageWithDatetime("Connecting..."))
            try:
                while True:
                    data, addr = listen_socket.recvfrom(1024)
            
                    if data:  
                        response = pickle.loads(data)
                        if response[1] != MY_PROCESS_ID and response[3] == 1: 
                            LEADER_IP = response[0]
                            LEADER_PID = response[1]
                            print(prefixMessageWithDatetime("Sucessfully joined the chatroom. IP adress of the leading Server: " +LEADER_IP))
                            print("")
                            return
            except socket.timeout: 
                pass
                
###################################### Main ##########################################

if __name__ == '__main__':
    
    # Starting client instance
    print(prefixMessageWithDatetime("Starting client instance..."))
    # Join the chat 
    join_thread = threading.Thread(target=join)
    join_thread.start()
    join_thread.join()
    
    message_thread = threading.Thread(target=send_chat_message)
    message_thread.start()
    
    listen_thread = threading.Thread(target=listen_for_messages)
    listen_thread.start()
    
    message_thread.join()
    listen_thread.join()