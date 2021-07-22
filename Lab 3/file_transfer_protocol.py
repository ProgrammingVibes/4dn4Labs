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
import sys
import argparse
import os
import threading

########################################################################

# Define all of the packet protocol field lengths. See the
# corresponding packet formats below.
CMD_FIELD_LEN = 1  # 1 byte commands sent from the client.
FILE_SIZE_FIELD_LEN = 8  # 8 byte file size field.
FILENAME_SIZE_FIELD_LEN = 8  # 8 byte filename size field.

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
    "get": 1,
    "put": 2,
    "list": 3,
    "bye": 4,
}

MSG_ENCODING = "utf-8"


########################################################################
# SERVER
########################################################################

class Server:
    HOSTNAME = "0.0.0.0"
    SERVICE_DISCOVERY_PORT = 30000
    PORT = 30001
    RECV_SIZE = 1024
    BACKLOG = 5

    SCAN_CMD = "SERVICE DISCOVERY"

    FILESHARE_SERVICE = "Vaibhav's File Sharing Service"
    FILESHARE_ENCODED = FILESHARE_SERVICE.encode(MSG_ENCODING)

    FILE_NOT_FOUND_MSG = "Error: Requested file is not available!"

    FOLDER_PREFIX = "Server/"

    def __init__(self):
        self.create_discovery_socket()
        self.create_listen_socket()
        os.chdir(Server.FOLDER_PREFIX)
        print(os.listdir())

        discovery_thread = threading.Thread(target=self.process_discovery_connections_forever)
        discovery_thread.start()

        self.accept_connections_forever()
        # self.create_listen_socket()
        # self.process_connections_forever()

    def create_discovery_socket(self):
        try:
            # Create an IPv4 UDP socket.
            self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Get socket layer socket options.
            self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind socket to socket address, i.e., IP address and port.
            self.discovery_socket.bind((Server.HOSTNAME, Server.SERVICE_DISCOVERY_PORT))
        except Exception as msg:
            print(msg)
            print("Exiting...")
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
            print("Exiting...")
            exit()

    def process_discovery_connections_forever(self):
        print("listening for service discovery messages on SDP port {} ...".format(Server.SERVICE_DISCOVERY_PORT))
        while True:
            try:
                recvd_bytes, address = self.discovery_socket.recvfrom(Server.RECV_SIZE)

                print("Discovery Socket Received: ", recvd_bytes.decode('utf-8'), " Address:", address)

                # Decode the received bytes back into strings.
                recvd_str = recvd_bytes.decode(MSG_ENCODING)

                # Check if the received packet contains a service scan
                # command.
                if Server.SCAN_CMD in recvd_str:
                    # Send the service advertisement message back to
                    # the client.
                    self.discovery_socket.sendto(Server.FILESHARE_ENCODED, address)
                    # new_thread = threading.Thread(target=self.handler)
                    # new_thread.daemon = True
                    # new_thread.start()
                    # recvd_str = ""
                    # recvd_bytes = None
                    # # self.create_discovery_socket()
            except KeyboardInterrupt:
                print()
                sys.exit(1)

    def accept_connections_forever(self):
        try:
            while True:
                client = self.socket.accept()
                connection, address = client
                print("-" * 72)
                print("Connection received from {}.".format(address))
                new_connection_thread = threading.Thread(target=self.process_connections_forever, args=(connection,))
                new_connection_thread.start()
                print(f"# of Active Threads: {threading.active_count()}")
        except KeyboardInterrupt:
            print()
            self.socket.close()
            sys.exit(1)

    def process_connections_forever(self, connection):
        try:
            while True:
                self.connection_handler(connection)
        except socket.error as e:
            # If the client has closed the connection, close the
            # socket on this end.
            print(e)
            print("Closing client connection ...")
            connection.close()
        except KeyboardInterrupt:
            print()
            self.socket.close()
            sys.exit(1)

    def connection_handler(self, connection):

        # Read the command and see if it is a GET.
        cmd = int.from_bytes(connection.recv(CMD_FIELD_LEN), byteorder='big')
        if cmd == CMD["get"]:
            filename_bytes = connection.recv(Server.RECV_SIZE)
            filename = filename_bytes.decode(MSG_ENCODING)

            try:
                file = open(filename, 'rb')
            except FileNotFoundError:
                print(Server.FILE_NOT_FOUND_MSG)
                return

            # Encode the file contents into bytes, record its size and
            # generate the file size field used for transmission.
            file_bytes = file.read()
            file.close()
            file_size_bytes = len(file_bytes)
            print(f"Found file! File size: {file_size_bytes} bytes")
            file_size_field = file_size_bytes.to_bytes(FILE_SIZE_FIELD_LEN, byteorder='big')

            # Create the packet to be sent with the header field.
            pkt = file_size_field + file_bytes

            # Send the packet to the connected client.
            connection.sendall(pkt)
            # print("Sent packet bytes: \n", pkt)
            print("Sending file: ", filename)

        if cmd == CMD["put"]:
            filename_len_bytes = connection.recv(FILENAME_SIZE_FIELD_LEN)
            filename_len = int.from_bytes(filename_len_bytes, byteorder='big')
            print(f"Receiving filename of length: {filename_len} bytes")

            filename_bytes = connection.recv(filename_len)
            filename = filename_bytes.decode(MSG_ENCODING)
            print(f"Receiving file: {filename}")

            file_size_bytes = connection.recv(FILE_SIZE_FIELD_LEN)
            file_size = int.from_bytes(file_size_bytes, byteorder='big')
            print(f"File Size: {file_size} bytes")
            recvd_bytes_total = bytearray()
            try:
                # Keep doing recv until the entire file is downloaded.
                while len(recvd_bytes_total) < file_size:
                    recvd_bytes_total += connection.recv(Server.RECV_SIZE)
                print(f"Received {len(recvd_bytes_total)} bytes")
                try:
                    file = open(filename, 'wb+')
                    file.write(recvd_bytes_total)
                    file.close()
                except FileNotFoundError:
                    print(Server.FILE_NOT_FOUND_MSG)
                    file.close()
            except KeyboardInterrupt:
                print("YOOOOOOOO")
                file.close()
                os.remove("./", file)
                exit(1)

        if cmd == CMD["list"]:
            listdir = os.listdir()
            listdir_bytes = str(listdir).encode(MSG_ENCODING)

            # Send the packet to the connected client.
            connection.sendall(listdir_bytes)
            # print("Sent packet bytes: \n", pkt)
            print("Sending list ...")

        if cmd == CMD["bye"]:
            print("Closing client connection ...")
            connection.close()
            exit()

########################################################################
# CLIENT
########################################################################

class Client:
    RECV_SIZE = 1024
    MSG_ENCODING = "utf-8"

    BROADCAST_ADDRESS = "255.255.255.255"
    SERVICE_PORT = 30000
    ADDRESS_PORT = (BROADCAST_ADDRESS, SERVICE_PORT)

    SCAN_CYCLES = 3
    SCAN_TIMEOUT = 5

    SCAN_CMD = "scan"
    CONNECT_CMD = "connect"
    GET_CMD = "get"
    PUT_CMD = "put"
    BYE_CMD = "bye"
    LLIST_CMD = "llist"
    RLIST_CMD = "rlist"
    LOCAL_CMDS = [SCAN_CMD, CONNECT_CMD, BYE_CMD, LLIST_CMD]
    SERVER_CMDS = [GET_CMD, PUT_CMD, RLIST_CMD]
    ALL_CMDS = LOCAL_CMDS + SERVER_CMDS

    SERVICE_DISCOVERY_MSG = "SERVICE DISCOVERY"
    SD_MSG_ENCODED = SERVICE_DISCOVERY_MSG.encode(MSG_ENCODING)

    INPUT_PARSER = argparse.ArgumentParser()
    INPUT_PARSER.add_argument("cmd")
    INPUT_PARSER.add_argument("--opt1", required=False)
    INPUT_PARSER.add_argument("--opt2", required=False)

    FILE_NOT_FOUND_MSG = "Error: Requested file is not available!"

    # Define the local file name where the downloaded file will be
    # saved.
    LOCAL_FILE_NAME = "localfile.txt"
    # LOCAL_FILE_NAME = "bee1.jpg"

    FOLDER_PREFIX = "Client/"

    def __init__(self):
        self.broadcast_socket = None
        self.transfer_socket = None
        self.connected = False
        os.chdir(Client.FOLDER_PREFIX)
        self.setup_broadcast_socket()
        self.setup_transfer_socket()
        self.handle_client_requests()

    def setup_broadcast_socket(self):
        try:
            self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            self.broadcast_socket.settimeout(Client.SCAN_TIMEOUT)
        except Exception as msg:
            print(msg)
            print("Exiting...")
            exit()

    def scan_for_service(self):
        scan_results = []

        try:
            for i in range(Client.SCAN_CYCLES):

                print(f"Sending broadcast scan {i}")
                self.broadcast_socket.sendto(Client.SD_MSG_ENCODED, Client.ADDRESS_PORT)

                while True:
                    try:
                        recvd_bytes, address = self.broadcast_socket.recvfrom(Client.RECV_SIZE)
                        recvd_msg = recvd_bytes.decode(Client.MSG_ENCODING)

                        if (recvd_msg, address) not in scan_results:
                            scan_results.append((recvd_msg, address))
                            continue

                    except socket.timeout:
                        break
        except KeyboardInterrupt:
            pass

        if scan_results:
            for result in scan_results:
                print(result)
        else:
            print("No services found.")

    def get_console_input(self):
        # In this version we keep prompting the user until a non-blank
        # line is entered.
        while True:
            input_args = input("Enter a command: ").split(' ')
            if len(input_args) >= 3:
                input_args.insert(2, "--opt2")
                input_args.insert(1, "--opt1")
            if len(input_args) == 2:
                input_args.insert(1, "--opt1")

            self.input_cmd = Client.INPUT_PARSER.parse_args(input_args)
            if self.input_cmd.cmd != "":
                break

    def setup_transfer_socket(self):
        try:
            self.transfer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as msg:
            print(msg)
            print("Exiting...")
            exit()

    def handle_client_requests(self):
        try:
            while True:
                self.get_console_input()

                if self.input_cmd.cmd == Client.SCAN_CMD:
                    self.scan_for_service()

                elif self.input_cmd.cmd == Client.CONNECT_CMD:
                    self.connect_to_server()

                elif self.input_cmd.cmd == Client.BYE_CMD:
                    if self.connected:
                        self.make_server_request()
                    self.connected = False
                    self.transfer_socket.close()
                    self.setup_transfer_socket()
                    print("Connection closed")

                elif self.input_cmd.cmd == Client.LLIST_CMD:
                    listdir = os.listdir()
                    print(listdir)

                elif self.input_cmd.cmd in Client.SERVER_CMDS:
                    if not self.connected:
                        print("Not connected to any file sharing service.")
                    else:
                        self.make_server_request()
                else:
                    print(f"{self.input_cmd.cmd} is not a valid command")

        except (KeyboardInterrupt) as e: # , EOFError
            print(e)
        except Exception as e:
            print(e)
        finally:
            print()
            print("Closing server connection ...")
            self.broadcast_socket.close()
            self.transfer_socket.close()
            print("Exiting...")
            exit()

    def connect_to_server(self):
        try:
            self.transfer_socket.connect((self.input_cmd.opt1, int(self.input_cmd.opt2)))
            self.connected = True
            print("Successfully connected to service")
        except Exception as msg:
            print(msg)

    def make_server_request(self):

        if self.input_cmd.cmd == Client.PUT_CMD:
            filename = self.input_cmd.opt1
            try:
                with open(filename, 'rb') as f:
                    file_bytes = f.read()
            except FileNotFoundError:
                print(Client.FILE_NOT_FOUND_MSG)
                return

            # Create the packet GET field.
            put_field = CMD["put"].to_bytes(CMD_FIELD_LEN, byteorder='big')

            # Create the packet filename field.
            filename_field = filename.encode(MSG_ENCODING)

            filename_len = len(filename_field)
            filename_len_field = filename_len.to_bytes(FILENAME_SIZE_FIELD_LEN, byteorder='big')

            # Create the packet.
            pkt = put_field + filename_len_field + filename_field

            # Send the request packet to the server.
            self.transfer_socket.sendall(pkt)

            # Encode the file contents into bytes, record its size and
            # generate the file size field used for transmission.
            file_size_bytes = len(file_bytes)
            file_size_field = file_size_bytes.to_bytes(FILE_SIZE_FIELD_LEN, byteorder='big')

            # Create the packet to be sent with the header field.
            pkt = file_size_field + file_bytes

            try:
                # Send the packet to the connected client.
                self.transfer_socket.sendall(pkt)
                # print("Sent packet bytes: \n", pkt)
                print("Sending file: ", filename)
            except socket.error as e:
                # If the server has closed the connection, close the
                # socket on this end.
                print(e)
                print("Closing server connection ...")
                self.connected = False
                self.transfer_socket.close()
                self.setup_transfer_socket()
                return

        if self.input_cmd.cmd == Client.GET_CMD:
            filename = self.input_cmd.opt1
            try:
                f = open(filename, 'wb+')
            except FileNotFoundError:
                print(Client.FILE_NOT_FOUND_MSG)
                return

            # Create the packet GET field.
            get_field = CMD["get"].to_bytes(CMD_FIELD_LEN, byteorder='big')

            # Create the packet filename field.
            filename_field = filename.encode(MSG_ENCODING)

            # Create the packet.
            pkt = get_field + filename_field

            # Send the request packet to the server.
            self.transfer_socket.sendall(pkt)

            file_size_bytes = self.transfer_socket.recv(FILE_SIZE_FIELD_LEN)
            file_size = int.from_bytes(file_size_bytes, byteorder='big')
            print(f"File Size: {file_size} bytes")
            recvd_bytes_total = bytearray()
            try:
                # Keep doing recv until the entire file is downloaded.
                while len(recvd_bytes_total) < file_size:
                    recvd_bytes_total += self.transfer_socket.recv(Client.RECV_SIZE)
                print(f"Received {len(recvd_bytes_total)} bytes")
                f.write(recvd_bytes_total)
            except KeyboardInterrupt:
                print()
                exit(1)
            # If the socket has been closed by the server, break out
            # and close it on this end.
            except socket.error as e:
                print(e)
                print("Closing server connection ...")
                self.connected = False
                self.transfer_socket.close()
                self.setup_transfer_socket()
            finally:
                f.close()

        if self.input_cmd.cmd == Client.RLIST_CMD:
            # Create the packet list field.
            list_field = CMD["list"].to_bytes(CMD_FIELD_LEN, byteorder='big')

            # Create the packet.
            pkt = list_field

            # Send the request packet to the server.
            self.transfer_socket.sendall(pkt)

            rlist_result_bytes = self.transfer_socket.recv(Client.RECV_SIZE)
            rlist_result = rlist_result_bytes.decode(Client.MSG_ENCODING)

            print(rlist_result)
        
        if self.input_cmd.cmd == Client.BYE_CMD:
            # Create the packet list field.
            bye_field = CMD["bye"].to_bytes(CMD_FIELD_LEN, byteorder='big')

            # Create the packet.
            pkt = bye_field

            # Send the request packet to the server.
            self.transfer_socket.sendall(pkt)



########################################################################

if __name__ == '__main__':
    roles = {'client': Client, 'server': Server}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles,
                        help='server or client role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()

########################################################################






