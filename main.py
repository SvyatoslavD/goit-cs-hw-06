from multiprocessing import Process

from datetime import datetime

import mimetypes
import pathlib
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

import socket
from concurrent import futures

import pymongo
import json


MONGO_DB_URI = "mongodb://mongo_db:27017/"
HTTP_SERVER_PORT = 3000
SOCKET_SERVER_PORT = 5000
MESSAGE_SIZE_MAX = 1024


class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        data_parse = urllib.parse.unquote_plus(data.decode())

        data_dict = {key: value for key, value in [
            el.split('=') for el in data_parse.split('&')]}
        data_dict["date"] = str(datetime.now())

        self.__send_request(str(data_dict))

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/contact':
            self.send_html_file('contact.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())

    def __send_request(self, message):
        def send_message(message):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                server = 'localhost', SOCKET_SERVER_PORT
                sock.connect(server)
                print(f'Connection established {server}')

                sock.send(message.encode())

            print(f'Data transfer completed')

        print(f'Sending {message} to the socket server')
        send_message(message)


class SocketServer:
    def __init__(self):
        self.__server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server_socket.bind(('localhost', SOCKET_SERVER_PORT))
        self.__server_socket.listen(10)

        print(f'Start socket server {self.__server_socket.getsockname()}')

    def serve_forever(self):
        def handle(sock: socket.socket, address: str):
            print(f'Connection established {address}')

            client = pymongo.MongoClient(MONGO_DB_URI)
            db = client["messages_db"]
            messages = db["messages"]

            received = sock.recv(MESSAGE_SIZE_MAX)
            data = received.decode()
            json_data = json.loads(data.replace("'", "\""))
            messages.insert_one(json_data)

            print(f'Message is saved: {received}')

            client.close()

            print(f'Socket connection closed {address}')

            sock.close()

        with futures.ThreadPoolExecutor(10) as client_pool:
            try:
                while True:
                    new_sock, address = self.__server_socket.accept()
                    client_pool.submit(handle, new_sock, address)
            except Exception as e:
                print(e)
            finally:
                print('Socket server is destroyed')

    def server_close(self):
        self.__server_socket.close()


def http_server_start():
    http = HTTPServer(('', HTTP_SERVER_PORT), HttpHandler)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


def socket_server_start():
    socket_server = SocketServer()
    try:
        socket_server.serve_forever()
    except KeyboardInterrupt:
        socket_server.server_close()


if __name__ == '__main__':
    p2 = Process(target=socket_server_start)
    p1 = Process(target=http_server_start)

    p1.start()
    p2.start()

    p1.join()
    p2.join()
