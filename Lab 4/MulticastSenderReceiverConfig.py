#!/usr/bin/env python3

########################################################################

import socket
import argparse
import sys
import time
import struct

########################################################################

# Read in the config.py file to set various addresses and ports.
from config import *

########################################################################
# Broadcast Server class
########################################################################

class Sender:

    # HOSTNAME = socket.gethostbyname('')
    HOSTNAME = 'localhost'

    TIMEOUT = 2
    RECV_SIZE = 256
    
    MSG_ENCODING = "utf-8"
    # MESSAGE =  HOSTNAME + "multicast beacon: "
    MESSAGE = "Hello from " 
    MESSAGE_ENCODED = MESSAGE.encode('utf-8')

    TTL = 1 # Hops
    TTL_SIZE = 1 # Bytes
    TTL_BYTE = TTL.to_bytes(TTL_SIZE, byteorder='big')
    # OR: TTL_BYTE = struct.pack('B', TTL)

    def __init__(self):
        self.create_listen_socket()
        self.send_messages_forever()

    def create_listen_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, Sender.TTL_BYTE)
            # self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, Sender.TTL)  # this works fine too
            # self.socket.bind(("192.168.2.37", 0))  # This line may be needed.
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def send_messages_forever(self):
        try:
            while True:
                print("Sending multicast packet (address, port): ", MULTICAST_ADDRESS_PORT)
                self.socket.sendto(Sender.MESSAGE_ENCODED, MULTICAST_ADDRESS_PORT)
                time.sleep(Sender.TIMEOUT)
        except Exception as msg:
            print(msg)
        except KeyboardInterrupt:
            print()
        finally:
            self.socket.close()
            sys.exit(1)

########################################################################
# Echo Receiver class
########################################################################

class Receiver:

    RECV_SIZE = 256

    def __init__(self):

        print("Bind address/port = ", BIND_ADDRESS_PORT)
        
        self.get_socket()
        self.receive_forever()

    def get_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

            # Bind to an address/port. In multicast, this is viewed as
            # a "filter" that determines what packets make it to the
            # UDP app.
            self.socket.bind(BIND_ADDRESS_PORT)

            ############################################################
            # The multicast_request must contain a bytes object
            # consisting of 8 bytes. The first 4 bytes are the
            # multicast group address. The second 4 bytes are the
            # interface address to be used. An all zeros I/F address
            # means all network interfaces.
            ############################################################
                        
            multicast_group_bytes = socket.inet_aton(MULTICAST_ADDRESS)

            print("Multicast Group: ", MULTICAST_ADDRESS)

            # Set up the interface to be used.
            multicast_if_bytes = socket.inet_aton(RX_IFACE_ADDRESS)

            # Form the multicast request.
            multicast_request = multicast_group_bytes + multicast_if_bytes

            # You can use struct.pack to create the request, but it is more complicated, e.g.,
            # 'struct.pack("<4sl", multicast_group_bytes,
            # int.from_bytes(multicast_if_bytes, byteorder='little'))'
            # or 'struct.pack("<4sl", multicast_group_bytes, socket.INADDR_ANY)'

            # Issue the Multicast IP Add Membership request.
            print("Adding membership (address/interface): ", MULTICAST_ADDRESS,"/", RX_IFACE_ADDRESS)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, multicast_request)
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def receive_forever(self):
        while True:
            try:
                data, address_port = self.socket.recvfrom(Receiver.RECV_SIZE)
                address, port = address_port
                print("Received: ", data.decode('utf-8'), " Address:", address, " Port: ", port)
            except KeyboardInterrupt:
                print(); exit()
            except Exception as msg:
                print(msg)
                sys.exit(1)

########################################################################
# Process command line arguments if run directly.
########################################################################

if __name__ == '__main__':
    roles = {'receiver': Receiver,'sender': Sender}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles, 
                        help='sender or receiver role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()

########################################################################






