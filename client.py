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
import random
from prompt_toolkit import PromptSession
session = PromptSession()
from prompt_toolkit.patch_stdout import patch_stdout

#################################### Variables #######################################
# Setup socket to get own IP adress
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
#
BROADCAST_IP = "192.168.178.255"
NEW_CLIENT_PORT = 9000
CLIENT_MESSAGING_PORT = 10000
TIMEOUT_INTERVALL = 3

MY_IP = f"127.0.0.{random.randint(1,254)}"
MY_PROCESS_ID = os.getpid()
LEADER_IP = ""
USERNAME = ""

#################################### Functions #######################################

def join():
    global USERNAME
    USERNAME = input(prefixMessageWithDatetime("Username: "))
    print(prefixMessageWithDatetime("Hello "+USERNAME+"!"))
    print(prefixMessageWithDatetime("Joining the chatroom..."))
    
    send_join_message(USERNAME)
    sys.exit(0)
                
def send_chat_message():
    # Create a UDP socket
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket to broadcast and enable reusing addresses
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind socket to address range and port
    listen_socket.bind(("", CLIENT_MESSAGING_PORT))
    listen_socket.settimeout(TIMEOUT_INTERVALL)
    
    while True:
        server_response = False
        with patch_stdout():
            message = session.prompt(prefixMessageWithDatetime(USERNAME+' > '))
            # message = input(prefixMessageWithDatetime("Message: "))
            broadcast(BROADCAST_IP, CLIENT_MESSAGING_PORT, pickle.dumps([MY_IP,message,USERNAME,""]) )
            print( "✔️", end="", flush=True)
            while True:
                try:
                    data, addr = listen_socket.recvfrom(1024)
                    if data : 
                        response = pickle.loads(data)
                        if response[0] != MY_IP:
                            server_response = True
                            print("✔️")
                            break
                            
                except socket.timeout: 
                    break            
            if server_response == False :   
                print("\n"+prefixMessageWithDatetime("Message could not be delivered. Reconnecting to Server..."))
                send_join_message(USERNAME)
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
                if response[0] != MY_IP and response[1] != MY_IP:
                    if response[0] == LEADER_IP:
                        print(prefixMessageWithDatetime(response[3])+" > "+response[2])
                    
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
    return datetime.now().strftime("%d.%m.%Y | %H:%M:%S")+" :: "+ message    

def send_join_message(username):
    # Create a UDP socket
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket to broadcast and enable reusing addresses
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind socket to address range and port
    listen_socket.bind((MY_IP, NEW_CLIENT_PORT)) 
    listen_socket.settimeout(2)
    
    while True:
            broadcast(BROADCAST_IP, NEW_CLIENT_PORT, str.encode(str(MY_PROCESS_ID)+"-"+str(MY_IP)+"-"+username))
            print(prefixMessageWithDatetime("Connecting..."))
            try:
                data, addr = listen_socket.recvfrom(1024)
        
                if data:  
                    response = data.decode()
                    response_array = response.split("-")
                    if response_array[1] != MY_IP:
                        global LEADER_IP
                        LEADER_IP = response_array[1]
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