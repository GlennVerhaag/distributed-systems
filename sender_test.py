import socket
import os
BROADCAST_IP = "172.25.191.255"
BROADCAST_PORT = 5001
BROADCAST_LISTENING_PORT = 5000
MY_PROCESS_ID = os.getpid()
MY_HOST = socket.gethostname()
MY_IP = socket.gethostbyname(socket.getfqdn())
SERVER_LIST={MY_PROCESS_ID:MY_IP}
CLIENT_LIST=[]
SERVER_GROUP = "224.1.1.1"
MULTICAST_PORT = 6001

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

print(get_ip_address())
broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Send message on broadcast address
broadcast_socket.sendto(str.encode(str(MY_PROCESS_ID)+"-"+str(MY_IP)), (BROADCAST_IP, BROADCAST_PORT))

multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 10)     
#multicast_socket.sendto(MY_IP.encode(), (SERVER_GROUP, MULTICAST_PORT))

