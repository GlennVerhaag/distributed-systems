import socket
import os
BROADCAST_IP = "172.25.191.255"
BROADCAST_PORT = 5000
BROADCAST_LISTENING_PORT = 5001
MY_PROCESS_ID = os.getpid()
MY_HOST = socket.gethostname()
MY_IP = socket.gethostbyname(MY_HOST)
SERVER_LIST={MY_PROCESS_ID:MY_IP}
CLIENT_LIST=[]

broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Send message on broadcast address
broadcast_socket.sendto(str.encode(str(MY_PROCESS_ID)+"-"+str(MY_IP)), (BROADCAST_IP, BROADCAST_PORT))
