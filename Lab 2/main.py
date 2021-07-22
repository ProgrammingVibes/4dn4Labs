#!/usr/bin/python3
"""


"""

import argparse
import csv
import getpass
import hashlib
import socket
import sys
from os import path


GET_MIDTERM_AVG_CMD = "GMA"
GET_LAB_1_AVG_CMD = "GL1A"
GET_LAB_2_AVG_CMD = "GL2A"
GET_LAB_3_AVG_CMD = "GL3A"
GET_LAB_4_AVG_CMD = "GL4A"
GET_GRADES = "GG"

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

    AVG_COMMANDS = {
        GET_MIDTERM_AVG_CMD.encode(MSG_ENCODING): MT_HEADER,
        GET_LAB_1_AVG_CMD.encode(MSG_ENCODING): L1_HEADER,
        GET_LAB_2_AVG_CMD.encode(MSG_ENCODING): L2_HEADER,
        GET_LAB_3_AVG_CMD.encode(MSG_ENCODING): L3_HEADER,
        GET_LAB_4_AVG_CMD.encode(MSG_ENCODING): L4_HEADER,
    }

    SOCKET_ADDRESS = (HOSTNAME, PORT)

    def __init__(self):
        self.socket = None
        self.data = {}
        self.load_csv_data()
        self.create_listen_socket()
        self.process_connections_forever()

    def load_csv_data(self):
        with open(path.join(path.dirname(__file__), "grades.csv")) as csvfile:
            reader = csv.DictReader(csvfile)
            print("Data read from CSV file:")
            for row in reader:
                print(
                    "  " + row[ID_HEADER],
                    row[PW_HEADER],
                    row[LN_HEADER],
                    row[FN_HEADER],
                    row[MT_HEADER],
                    row[L1_HEADER],
                    row[L2_HEADER],
                    row[L3_HEADER],
                    row[L4_HEADER],
                    sep=",",
                )
                password = row[PW_HEADER].encode("utf-8")
                ID = row[ID_HEADER].encode("utf-8")
                m = hashlib.sha256()
                m.update(ID)
                m.update(password)
                hash = m.digest()
                self.data[hash] = row

    def create_listen_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

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
        print(f"Connection received from {address_port[0]} on port {address_port[1]}.")

        while True:
            try:
                recvd_bytes = connection.recv(GradeRetrievalServer.RECV_BUFFER_SIZE)

                if len(recvd_bytes) == 0:
                    print("Closing client connection ... ")
                    connection.close()
                    break

                if recvd_bytes in GradeRetrievalServer.AVG_COMMANDS:
                    print(f"Received {recvd_bytes.decode(GradeRetrievalServer.MSG_ENCODING)} command from client")
                    average_str = str(self.calculate_average(GradeRetrievalServer.AVG_COMMANDS[recvd_bytes]))
                    bytes_to_send = average_str.encode(GradeRetrievalServer.MSG_ENCODING)
                else:
                    print(f"Received IP/password hash {str(recvd_bytes)} from client")
                    if recvd_bytes in self.data:
                        print("Correct password, record found")
                        bytes_to_send = self.format_grades(recvd_bytes)
                    else:
                        print("Incorrect ID/Password")
                        bytes_to_send = "Incorrect ID/Password".encode(GradeRetrievalServer.MSG_ENCODING)

                connection.sendall(bytes_to_send)

            except KeyboardInterrupt:
                print()
                print("Closing client connection ... ")
                connection.close()
                break

    def calculate_average(self, grade_header):
        total = 0
        entries = 0
        for entry in self.data.values():
            entries += 1
            total += int(entry[grade_header])

        return total / entries

    def format_grades(self, recvd_hash):
        entry = self.data[recvd_hash]
        formatted_str = f"Midterm: {entry[MT_HEADER]}\n" \
            + f"Lab 1: {entry[L1_HEADER]}\n" \
            + f"Lab 2: {entry[L2_HEADER]}\n" \
            + f"Lab 3: {entry[L3_HEADER]}\n" \
            + f"Lab 4: {entry[L4_HEADER]}\n"

        return formatted_str.encode(GradeRetrievalServer.MSG_ENCODING)


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
            self.socket.connect((GradeRetrievalClient.SERVER_HOSTNAME, GradeRetrievalServer.PORT))
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def get_console_input(self):
        # In this version we keep prompting the user until a non-blank
        # line is entered.
        while True:
            self.input_text = input("Enter a command: ")
            print(f"Command entered: {self.input_text}")
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

            if (self.input_text == GET_GRADES):
                self.get_grades_send()
            else:
                self.normal_send()

        except Exception as msg:
            print(msg)
            sys.exit(1)

    def connection_receive(self):
        try:
            # Receive and print out text. The received bytes objects
            # must be decoded into string objects.
            recvd_bytes = self.socket.recv(GradeRetrievalClient.RECV_BUFFER_SIZE)

            # recv will block if nothing is available. If we receive
            # zero bytes, the connection has been closed from the
            # other end. In that case, close the connection on this
            # end and exit.
            if len(recvd_bytes) == 0:
                print("Closing server connection ... ")
                self.socket.close()
                sys.exit(1)

            print("Received: ", recvd_bytes.decode(GradeRetrievalServer.MSG_ENCODING))

        except Exception as msg:
            print(msg)
            sys.exit(1)

    def normal_send(self):
        try:
            # Send string objects over the connection. The string must
            # be encoded into bytes objects first.
            if self.input_text == GET_MIDTERM_AVG_CMD:
                print("Fetching midterm average:")
            if self.input_text == GET_LAB_1_AVG_CMD:
                print("Fetching lab 1 average:")
            if self.input_text == GET_LAB_2_AVG_CMD:
                print("fetching lab 2 average:")
            if self.input_text == GET_LAB_3_AVG_CMD:
                print("fetching lab 3 average:")
            if self.input_text == GET_LAB_4_AVG_CMD:
                print("fetching lab 4 average:")

            self.socket.sendall(self.input_text.encode(GradeRetrievalServer.MSG_ENCODING))
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def get_grades_send(self):
        try:
            ID = input('What is your username? ')
            password = getpass.getpass(prompt='What is your password? ')
            print(f"ID number {ID} and password {password} received.")

            password = password.encode(GradeRetrievalServer.MSG_ENCODING)
            ID = ID.encode(GradeRetrievalServer.MSG_ENCODING)
            m = hashlib.sha256()
            m.update(ID)
            m.update(password)
            hash = m.digest()

            self.socket.sendall(hash)
            print(f"ID/password hash {hash} sent to server")

        except Exception as msg:
            print(msg)
            sys.exit(1)


if __name__ == '__main__':
    roles = {'client': GradeRetrievalClient,'server': GradeRetrievalServer}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles,
                        help='server or client role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()
