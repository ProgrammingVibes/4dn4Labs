#!/usr/bin/env python3

########################################################################

import argparse
import json
import socket
import sys
import threading
import keyboard
from signal import pthread_kill, SIGINT

########################################################################


CMD_FIELD_LEN = 1  # 1 byte commands sent from the client
CHATROOM_NAME_LEN_FIELD_LEN = 4  # 4 byte chatroom name field.
CHATROOM_ADDRESS_FIELD_LEN = 4  # 4 byte chatroom addr field.
CHATROOM_PORT_FIELD_LEN = 4  # 4 byte chatroom port field.

MSG_ENCODING = "utf-8"

SERVER_CMD = {
    "getdir": 1,
    "makeroom": 2,
    "deleteroom": 3,
    "bye": 4,
}

########################################################################
# Group Chat Server class (Chat Room Discovery Server) [CRDS]
########################################################################


class GroupChatServer:
    HOSTNAME = "0.0.0.0"
    PORT = 30001
    RECV_SIZE = 1024
    BACKLOG = 5

    def __init__(self):
        self.chat_rooms = {}
        self.create_listen_socket()
        self.accept_connections_forever()

    def create_listen_socket(self):
        try:
            # Create the TCP server listen socket in the usual way.
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((GroupChatServer.HOSTNAME, GroupChatServer.PORT))
            self.socket.listen(GroupChatServer.BACKLOG)
            print("listening for chatroom commands on port {} ...".format(GroupChatServer.PORT))
        except Exception as msg:
            print(msg)
            print("Exiting...")
            exit()

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
        if cmd == SERVER_CMD["getdir"]:
            x = json.dumps(self.chat_rooms)
            bytes_to_send = x.encode(MSG_ENCODING)
            connection.sendall(bytes_to_send)

        if cmd == SERVER_CMD["makeroom"]:
            print("Making room...")
            chatroom_name_len = int.from_bytes(connection.recv(CHATROOM_NAME_LEN_FIELD_LEN), byteorder='big')

            chatroom_name_bytes = connection.recv(chatroom_name_len)
            chat_room_name = chatroom_name_bytes.decode(MSG_ENCODING)
            
            chat_address_bytes=connection.recv(CHATROOM_ADDRESS_FIELD_LEN)
            chat_address = socket.inet_ntoa(chat_address_bytes)

            port_address_bytes = connection.recv(CHATROOM_PORT_FIELD_LEN)
            port_address = int.from_bytes(port_address_bytes, byteorder='big')

            self.chat_rooms[chat_room_name] = (chat_address, port_address)
            print("Chatroom made!")


        if cmd == SERVER_CMD["deleteroom"]:
            chatroom_name_len = int.from_bytes(connection.recv(CHATROOM_NAME_LEN_FIELD_LEN), byteorder='big')

            chatroom_name_bytes = connection.recv(chatroom_name_len)
            chat_room_name = chatroom_name_bytes.decode(MSG_ENCODING)

            del (self.chat_rooms[chat_room_name])

        if cmd == SERVER_CMD["bye"]:
            print("Closing client connection ...")
            connection.close()
            exit()




class GroupChatClient:
    RX_IFACE_ADDRESS = "0.0.0.0"
    RECV_SIZE = 1024
    
    NAME_CMD = "name"
    CHAT_CMD = "chat"
    GETDIR_CMD = "getdir"
    MAKEROOM_CMD = "makeroom"
    DELETEROOM_CMD = "deleteroom"
    CONNECT_CMD = "connect"
    BYE_CMD = "bye"
    
    CLIENT_CMDS = (
        NAME_CMD,
        CHAT_CMD,
        CONNECT_CMD,
        BYE_CMD,
    )

    SERVER_CMDS = (
        GETDIR_CMD,
        MAKEROOM_CMD,
        DELETEROOM_CMD,
    )

    TTL = 1 # Hops
    TTL_SIZE = 1 # Bytes
    TTL_BYTE = TTL.to_bytes(TTL_SIZE, byteorder='big')
    # OR: TTL_BYTE = struct.pack('B', TTL)

    INPUT_PARSER = argparse.ArgumentParser()
    INPUT_PARSER.add_argument("cmd")
    INPUT_PARSER.add_argument("--opt1", required=False)
    INPUT_PARSER.add_argument("--opt2", required=False)
    INPUT_PARSER.add_argument("--opt3", required=False)

    def __init__(self):
        self.server_socket = None
        self.send_socket = None
        self.receive_socket = None
        
        self.connected = False
        self.chat_mode = False
        self.input_cmd = None
        self.getdir_results = None
        self.username = "Anon"
        self.chatroom_addr_port = None

        keyboard.add_hotkey('ctrl+q', self.exit_chat_mode)

        self.create_server_socket()
        self.handle_requests_forever()

    def create_server_socket(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as msg:
            print(msg)
            print("Exiting...")
            exit()

    def connect_to_server(self):
        try:
            self.server_socket.connect( (GroupChatServer.HOSTNAME, GroupChatServer.PORT) )
            self.connected = True
            print("Successfully connected to service")
        except Exception as msg:
            print(msg)

    def create_send_socket(self):
        try:
            self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.send_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, GroupChatClient.TTL_BYTE)
            # self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, Sender.TTL)  # this works fine too
            # self.socket.bind(("192.168.2.37", 0))  # This line may be needed.
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def create_receive_socket(self):
        try:
            # Create an IPv4 UDP socket
            self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Get socket layer socket options.
            self.receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind socket to socket address, i.e., IP address and port.
            self.receive_socket.bind(self.chatroom_addr_port)

            ############################################################
            # The multicast_request must contain a bytes object
            # consisting of 8 bytes. The first 4 bytes are the
            # multicast group address. The second 4 bytes are the
            # interface address to be used. An all zeros I/F address
            # means all network interfaces.
            ############################################################
            
            multicast_group_bytes = socket.inet_aton(self.chatroom_addr_port[0])

            print("Multicast Group: ", self.chatroom_addr_port[0])

            # Set up the interface to be used.
            multicast_if_bytes = socket.inet_aton(GroupChatClient.RX_IFACE_ADDRESS)

            # Form the multicast request.
            multicast_request = multicast_group_bytes + multicast_if_bytes

            # You can use struct.pack to create the request, but it is more complicated, e.g.,
            # 'struct.pack("<4sl", multicast_group_bytes,
            # int.from_bytes(multicast_if_bytes, byteorder='little'))'
            # or 'struct.pack("<4sl", multicast_group_bytes, socket.INADDR_ANY)'

            # Issue the Multicast IP Add Membership request.
            print("Adding membership (address/interface): ", self.chatroom_addr_port[0],"/", GroupChatClient.RX_IFACE_ADDRESS)
            self.receive_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, multicast_request)
        
        except Exception as msg:
            print(msg)
            print("Exiting...")
            sys.exit(1)

    def get_console_input(self):
        # In this version we keep prompting the user until a non-blank
        # line is entered.
        prompt = ("(Connected) " if self.connected else "") + "Enter a command: " 
        while True:
            input_args = input(prompt).split(' ')
            if len(input_args) >= 4:
                input_args.insert(3, "--opt3")
                input_args.insert(2, "--opt2")
                input_args.insert(1, "--opt1")
            elif len(input_args) == 3:
                input_args.insert(2, "--opt2")
                input_args.insert(1, "--opt1")
            elif len(input_args) == 2:
                input_args.insert(1, "--opt1")

            self.input_cmd = GroupChatClient.INPUT_PARSER.parse_args(input_args)
            if self.input_cmd.cmd != "":
                break

    def handle_requests_forever(self):
        try:
            while True:
                self.get_console_input()

                if self.input_cmd.cmd == GroupChatClient.CONNECT_CMD:
                    self.connect_to_server()

                elif self.input_cmd.cmd == GroupChatClient.NAME_CMD:
                    self.set_username()

                elif self.input_cmd.cmd == GroupChatClient.CHAT_CMD:
                    self.chat()

                elif self.input_cmd.cmd == GroupChatClient.BYE_CMD:
                    if self.connected:
                        self.make_server_request()
                    self.connected = False
                    self.server_socket.close()
                    self.create_server_socket()
                    print("Connection closed")

                elif self.input_cmd.cmd in GroupChatClient.SERVER_CMDS:
                    if not self.connected:
                        print("Not connected to any chatroom service.")
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
            self.server_socket.close()
            print("Exiting...")
            exit()

    def set_username(self):
        self.username = self.input_cmd.opt1

    def chat(self): #logged on and ready to chat

        if self.input_cmd.opt1 not in self.getdir_results:
            print("Chatroom does not exist.")
            return

        self.chatroom_addr_port = tuple(self.getdir_results[self.input_cmd.opt1])

        self.create_send_socket()
        self.create_receive_socket()
        recvThread = threading.Thread(target=self.receivemsg, daemon=True)

        self.chat_mode = True
        recvThread.start()
        self.sendmsg_forever()

        self.send_socket.close()
        self.receive_socket.close()

    def receivemsg(self):
        while (self.chat_mode):
            try:
                msg_bytes = self.receive_socket.recv(GroupChatClient.RECV_SIZE)
                msg_decode = msg_bytes.decode(MSG_ENCODING)
                print(msg_decode)
            except KeyboardInterrupt:
                exit(1)
                pass

    def sendmsg_forever(self):
        try:
            while (self.chat_mode):
                msg = input("enter a message: ")
                fullmsg = self.username + " : " + msg
                fullmsg_encoded = fullmsg.encode(MSG_ENCODING)
                self.send_socket.sendto(fullmsg_encoded, self.chatroom_addr_port)
        except KeyboardInterrupt:
            print("You left the chatroom.")

    def exit_chat_mode(self):
        if self.chat_mode:
            self.chat_mode = False
            print("You left the chatroom. Press enter to continue.")

    def getdir(self):
        command = SERVER_CMD["getdir"]
        bytes_to_send = command.to_bytes(CMD_FIELD_LEN, byteorder='big')
        self.server_socket.sendall(bytes_to_send)

        result_bytes = self.server_socket.recv(GroupChatClient.RECV_SIZE)
        print(result_bytes)
        print(result_bytes.decode(MSG_ENCODING))
        self.getdir_results = json.loads(result_bytes.decode(MSG_ENCODING))

        print(json.dumps(self.getdir_results, indent=2)) #wow json stop taking so many dumps

    def makeroom(self):
        command = SERVER_CMD["makeroom"]
        command_field = command.to_bytes(CMD_FIELD_LEN, byteorder='big')

        chatroom_name = self.input_cmd.opt1
        chatroom_name_len = len(chatroom_name)
        chatroom_name_len_field = chatroom_name_len.to_bytes(CHATROOM_NAME_LEN_FIELD_LEN, byteorder='big')
        chatroom_field = chatroom_name.encode(MSG_ENCODING)

        address = self.input_cmd.opt2
        address_field = socket.inet_aton(address)

        port = int(self.input_cmd.opt3)
        port_field = port.to_bytes(CHATROOM_PORT_FIELD_LEN, byteorder='big')

        # Create the packet.
        pkt = command_field + chatroom_name_len_field + chatroom_field + address_field + port_field

        # Send the request packet to the server.
        self.server_socket.sendall(pkt)


    def deleteroom(self):
        command = SERVER_CMD["deleteroom"]
        command_field = command.to_bytes(CMD_FIELD_LEN, byteorder='big')

        chatroom_name = self.input_cmd.opt1
        chatroom_name_len = len(chatroom_name)
        chatroom_name_len_field = chatroom_name_len.to_bytes(CHATROOM_NAME_LEN_FIELD_LEN, byteorder='big')
        chatroom_field = chatroom_name.encode(MSG_ENCODING)

        # Create the packet.
        pkt = command_field + chatroom_name_len_field + chatroom_field 

        # Send the request packet to the server.
        self.server_socket.sendall(pkt)

    def make_server_request(self):

        if self.input_cmd.cmd == GroupChatClient.GETDIR_CMD:
            self.getdir()

        if self.input_cmd.cmd == GroupChatClient.MAKEROOM_CMD:
            self.makeroom()

        if self.input_cmd.cmd == GroupChatClient.DELETEROOM_CMD:
            self.deleteroom()
        
        if self.input_cmd.cmd == GroupChatClient.BYE_CMD:
            # Create the packet list field.
            bye_field = SERVER_CMD["bye"].to_bytes(CMD_FIELD_LEN, byteorder='big')

            # Create the packet.
            pkt = bye_field

            # Send the request packet to the server.
            self.server_socket.sendall(pkt)


class ExitChatMode(Exception):
    pass

########################################################################
# Process command line arguments if run directly.
########################################################################

if __name__ == '__main__':
    roles = {'server': GroupChatServer, 'client': GroupChatClient}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles, 
                        help='sender or receiver role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()

########################################################################
