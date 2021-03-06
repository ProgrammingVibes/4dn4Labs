#!/usr/bin/env python3

########################################################################
#
# GET File Transfer
#
# When the client connects to the server, it immediately sends a
# 1-byte GET command followed by the requested filename. The server
# checks for the GET and then transmits the file. The file transfer
# from the server is prepended by an 8 byte file size field. These
# formats are shown below.
#
# The server needs to have REMOTE_FILE_NAME defined as a text file
# that the client can request. The client will store the downloaded
# file using the filename LOCAL_FILE_NAME. This is so that you can run
# a server and client from the same directory without overwriting
# files.
#
########################################################################

import socket
import argparse
import os
import threading
########################################################################

# Define all of the packet protocol field lengths. See the
# corresponding packet formats below.
CMD_FIELD_LEN = 1 # 1 byte commands sent from the client.
FILE_SIZE_FIELD_LEN  = 8 # 8 byte file size field.

# Packet format when a GET command is sent from a client, asking for a
# file download:

# -------------------------------------------
# | 1 byte GET command  | ... file name ... |
# -------------------------------------------

# When a GET command is received by the server, it reads the file name
# then replies with the following response:

# -----------------------------------
# | 8 byte file size | ... file ... |
# -----------------------------------

# Define a dictionary of commands. The actual command field value must
# be a 1-byte integer. For now, we only define the "GET" command,
# which tells the server to send a file.

CMD = { 
    "get" : 1,
    "put" : 2, 
    "list": 3,
}

MSG_ENCODING = "utf-8"
    
########################################################################
# SERVER
########################################################################

class Server:

    HOSTNAME = "0.0.0.0"
    SERVICE_DISCOVERY_PORT= 30000
    PORT = 30001
    RECV_SIZE = 1024
    BACKLOG = 5

    SCAN_CMD = "SERVICE DISCOVERY"

    FILESHARE_SERVICE="Vaibhav's File Sharing Service"
    FILESHARE_ENCODED=FILESHARE_SERVICE.encode(MSG_ENCODING)

    FILE_NOT_FOUND_MSG = "Error: Requested file is not available!"

    # This is the file that the client will request using a GET.
    REMOTE_FILE_NAME = "remotefile.txt"
    # REMOTE_FILE_NAME = "bee.jpg"

    def __init__(self):
        self.create_discovery_socket()
        self.create_listen_socket()
        discovery_thread=threading.Thread(target=self.process_discovery_connections_forever)
        discovery_thread.start()

        connections_thread=threading.Thread(target=self.process_connections_forever)
        self.process_disconnections_forever()
        #self.create_listen_socket()
        #self.process_connections_forever()
    
    def handler(self):
        #self.create_listen_socket()
        self.process_connections_forever()


    def create_discovery_socket(self):
        try:
            # Create an IPv4 UDP socket.
            self.discoverySocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Get socket layer socket options.
            self.discoverySocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind socket to socket address, i.e., IP address and port.
            self.discoverySocket.bind( (Server.HOSTNAME, Server.SERVICE_DISCOVERY_PORT) )
        except Exception as msg:
            print(msg)
            sys.exit(1)


    def create_listen_socket(self):
        try:
            # Create the TCP server listen socket in the usual way.
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((Server.HOSTNAME, Server.PORT))
            self.socket.listen(Server.BACKLOG)
            print("listening for file sharing connections on port {} ...".format(Server.PORT))
        except Exception as msg:
            print(msg)
            exit()

    def process_discovery_connections_forever(self):
        i=0
        while True:
            try:
                print("loopq")
                print("listening for service discovery messages on SDP port {} ...".format(Server.SERVICE_DISCOVERY_PORT))
                recvd_bytes, address = self.discoverySocket.recvfrom(Server.RECV_SIZE)

                print("Received: ", recvd_bytes.decode('utf-8'), " Address:", address)
            
                # Decode the received bytes back into strings.
                recvd_str = recvd_bytes.decode(MSG_ENCODING)

                # Check if the received packet contains a service scan
                # command.
                if Server.SCAN_CMD in recvd_str:
                    print("we got herea")
                    # Send the service advertisement message back to
                    # the client.
                    self.discoveryocket.sendto(Server.FILESHARE_ENCODED, address)
                    new_thread=threading.Thread(target=self.handler)
                    new_thread.daemon = True
                    new_thread.start()
                    recvd_str=""
                    recvd_bytes=None
                    #self.create_discovery_socket()
            except KeyboardInterrupt:
                print()
                sys.exit(1)        

    def process_connections_forever(self):
        try:
            while True:
                self.connection_handler(self.socket.accept())
        except KeyboardInterrupt:
            print()
            self.socket.close()
            sys.exit(1)
#        finally
#            self.socket.close()



    def connection_handler(self, client):
        connection, address = client
        print("-" * 72)
        print("Connection received from {}.".format(address))

        # Read the command and see if it is a GET.
        cmd = int.from_bytes(connection.recv(CMD_FIELD_LEN), byteorder='big')
        filename_bytes = connection.recv(Server.RECV_SIZE)
        filename = filename_bytes.decode(MSG_ENCODING)
        if cmd == CMD["get"]:

            try:
                file = open(filename, 'rb')
            except FileNotFoundError:
                print(Server.FILE_NOT_FOUND_MSG)                 
                return

            # Encode the file contents into bytes, record its size and
            # generate the file size field used for transmission.
            file_bytes = file.read()
            file_size_bytes = len(file_bytes)
            file_size_field = file_size_bytes.to_bytes(FILE_SIZE_FIELD_LEN, byteorder='big')

            # Create the packet to be sent with the header field.
            pkt = file_size_field + file_bytes
        
            try:
                # Send the packet to the connected client.
                connection.sendall(pkt)
                # print("Sent packet bytes: \n", pkt)
                print("Sending file: ", filename)
            except socket.error:
                # If the client has closed the connection, close the
                # socket on this end.
                print("Closing client connection ...")
                connection.close()
                return
            file.close()

        if cmd == CMD["put"]:

            try:
                file = open(filename, 'wb+')
            except FileNotFoundError:
                print(Server.FILE_NOT_FOUND_MSG)
                connection.close()                   
                return
            file_size_bytes = self.socket_recv_size(FILE_SIZE_FIELD_LEN)
            file_size = int.from_bytes(file_size_bytes, byteorder='big')
            recvd_bytes_total = bytearray()
            try:
            # Keep doing recv until the entire file is downloaded. 
                while len(recvd_bytes_total) < file_size:
                    recvd_bytes_total += self.socket.recv(Client.RECV_SIZE)
                file.write(recvd_bytes_total)
                file.close()
            except KeyboardInterrupt:
                print()
                exit(1)
            # If the socket has been closed by the server, break out
            # and close it on this end.
            except socket.error:
                self.socket.close()   
        
        if cmd == CMD["list"]:
            listdir=os.listdir()
            listdir_bytes=listdir.encode(MSG_ENCODING)
            try:
                # Send the packet to the connected client.
                connection.sendall(listdir_bytes)
                # print("Sent packet bytes: \n", pkt)
                print("Sending list ...")
            except socket.error:
                # If the client has closed the connection, close the
                # socket on this end.
                print("Closing client connection ...")
                connection.close()
                return

  



########################################################################
# CLIENT
########################################################################

class Client:

    RECV_SIZE = 10

    # Define the local file name where the downloaded file will be
    # saved.
    LOCAL_FILE_NAME = "localfile.txt"
    # LOCAL_FILE_NAME = "bee1.jpg"

    def __init__(self):
        self.get_socket()
        self.connect_to_server()
        self.get_file()

    def get_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as msg:
            print(msg)
            exit()

    def connect_to_server(self):
        try:
            self.socket.connect((Server.HOSTNAME, Server.PORT))
        except Exception as msg:
            print(msg)
            exit()

    def socket_recv_size(self, length):
        bytes = self.socket.recv(length)
        if len(bytes) < length:
            self.socket.close()
            exit()
        return(bytes)
            
    def get_file(self):

        # Create the packet GET field.
        get_field = CMD["GET"].to_bytes(CMD_FIELD_LEN, byteorder='big')

        # Create the packet filename field.
        filename_field = Server.REMOTE_FILE_NAME.encode(MSG_ENCODING)

        # Create the packet.
        pkt = get_field + filename_field

        # Send the request packet to the server.
        self.socket.sendall(pkt)

        # Read the file size field.
        file_size_bytes = self.socket_recv_size(FILE_SIZE_FIELD_LEN)
        if len(file_size_bytes) == 0:
               self.socket.close()
               return

        # Make sure that you interpret it in host byte order.
        file_size = int.from_bytes(file_size_bytes, byteorder='big')

        # Receive the file itself.
        recvd_bytes_total = bytearray()
        try:
            # Keep doing recv until the entire file is downloaded. 
            while len(recvd_bytes_total) < file_size:
                recvd_bytes_total += self.socket.recv(Client.RECV_SIZE)

            # Create a file using the received filename and store the
            # data.
            print("Received {} bytes. Creating file: {}" \
                  .format(len(recvd_bytes_total), Client.LOCAL_FILE_NAME))

            with open(Client.LOCAL_FILE_NAME, 'w') as f:
                f.write(recvd_bytes_total.decode(MSG_ENCODING))
        except KeyboardInterrupt:
            print()
            exit(1)
        # If the socket has been closed by the server, break out
        # and close it on this end.
        except socket.error:
            self.socket.close()
            
########################################################################

if __name__ == '__main__':
    roles = {'client': Client,'server': Server}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles, 
                        help='server or client role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()

########################################################################






