#!/usr/bin/python3
"""


"""

import argparse
import csv
import socket
import sys
from os import path
import hashlib


GET_MIDTERM_AVG_CMD = "GMA"
GET_LAB_1_AVG_CMD = "GL1A"
GET_LAB_2_AVG_CMD = "GL2A"
GET_LAB_3_AVG_CMD = "GL3A"
GET_LAB_4_AVG_CMD = "GL4A"

ID_HEADER = "ID Number"
PW_HEADER = "Password"
LN_HEADER = "Last Name"
FN_HEADER = "First Name"
MT_HEADER = "Midterm"
L1_HEADER = "Lab 1"
L2_HEADER = "Lab 2"
L3_HEADER = "Lab 3"
L4_HEADER = "Lab 4"


class GradeRetrievalServer:
    HOSTNAME = "0.0.0.0"
    PORT = 50000

    RECV_BUFFER_SIZE = 1024
    MAX_CONNECTION_BACKLOG = 10

    MSG_ENCODING = "utf-8"

    SOCKET_ADDRESS = (HOSTNAME, PORT)

    def __init__(self):
        self.socket = None
        self.data = {}

    def load_csv_data(self):
        with open(path.join(path.dirname(__file__), "grades.csv")) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                self.data[row[ID_HEADER]] = row

    def create_listen_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self.socket.bind(GradeRetrievalServer.SOCKET_ADDRESS)

            self.socket.listen(GradeRetrievalServer.MAX_CONNECTION_BACKLOG)
            print(f"Listening for connections on port "
                  f"{GradeRetrievalServer.PORT}")
        except Exception as err:
            print(err)
            sys.exit(1)

    def process_connections_forever(self):
        try:
            while True:
                # Block while waiting for accepting incoming
                # connections. When one is accepted, pass the new
                # (cloned) socket reference to the connection handler
                # function.
                self.connection_handler(self.socket.accept())
        except Exception as msg:
            print(msg)
        except KeyboardInterrupt:
            print()
        finally:
            self.socket.close()
            sys.exit(1)

    def connection_handler(self, client):
        connection, address_port = client

        while True:
            try:
                recvd_bytes = 0

                while recvd_bytes == 0:
                    recvd_bytes = connection.recv(GradeRetrievalServer.RECV_BUFFER_SIZE)

                # Decode the received bytes back into strings. Then output
                # them.
                recvd_str = recvd_bytes.decode(GradeRetrievalServer.MSG_ENCODING)
                print("Received: ", recvd_str)

                # Send the received bytes back to the client.
                connection.sendall(recvd_bytes)
                print("Sent: ", recvd_str)

            except KeyboardInterrupt:
                print()
                print("Closing client connection ... ")
                connection.close()
                break
                

class GradeRetrievalClient:
    SERVER_HOSTNAME = socket.gethostbyname('0.0.0.0')

    RECV_BUFFER_SIZE = 1024

    def __init__(self):
        self.get_socket()
        self.connect_to_server()
        self.send_console_input_forever()
    
    def get_socket(self):
        try:
            # Create an IPv4 TCP socket.
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as msg:
            print(msg)
            sys.exit(1)
            
    def connect_to_server(self):
        try:
            # Connect to the server using its socket address tuple.
            self.socket.connect((Client.SERVER_HOSTNAME, Server.PORT))
        except Exception as msg:
            print(msg)
            sys.exit(1)
            
    def get_console_input(self):
        # In this version we keep prompting the user until a non-blank
        # line is entered.
        while True:
            self.input_text = input("Enter a command: ")
            if self.input_text != "":
                break
    
    def send_console_input_forever(self):
        while True:
            try:
                self.get_console_input()
                self.connection_send()
                self.connection_receive()
            except (KeyboardInterrupt, EOFError):
                print()
                print("Closing server connection ...")
                self.socket.close()
                sys.exit(1)
                
    def connection_send(self):
        try:
            # Send string objects over the connection. The string must
            # be encoded into bytes objects first.
            if(self.input_text==GET_MIDTERM_AVG_CMD):
            		print("Fetching midterm average:")
            if(self.input_text==GET_LAB_1_AVG_CMD):
            		print("Fetching lab 1 average:")
            if(self.input_text==GET_LAB_2_AVG_CMD):
            		print("fetching lab 2 average:")
            if(self.input_text==GET_LAB_3_AVG_CMD):
            		print("fetching lab 3 average:")
            if(self.input_text==GET_LAB_4_AVG_CMD):
            		print("fetching lab 4 average:")
            
            self.socket.sendall(self.input_text.encode(Server.MSG_ENCODING))
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def connection_receive(self):
        try:
            # Receive and print out text. The received bytes objects
            # must be decoded into string objects.
            recvd_bytes = self.socket.recv(Client.RECV_BUFFER_SIZE)

            # recv will block if nothing is available. If we receive
            # zero bytes, the connection has been closed from the
            # other end. In that case, close the connection on this
            # end and exit.
            if len(recvd_bytes) == 0:
                print("Closing server connection ... ")
                self.socket.close()
                sys.exit(1)

            print("Received: ", recvd_bytes.decode(Server.MSG_ENCODING))

        except Exception as msg:
            print(msg)
            sys.exit(1)

if __name__ == '__main__':
    print("Hello")
