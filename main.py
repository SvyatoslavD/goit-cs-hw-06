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

class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        print(data)
        data_parse = urllib.parse.unquote_plus(data.decode())
        print(data_parse)
        data_dict = {key: value for key, value in [
            el.split('=') for el in data_parse.split('&')]}
        data_dict["date"] = str(datetime.now())
        print(data_dict)
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
        TCP_IP = 'localhost'
        TCP_PORT = 5000
        #MESSAGE = "Python Web development"

        def run_client(ip: str, port: int, message):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                server = ip, port

                sock.connect(server)
                print(f'Connection established {server}')

                sock.send(message.encode())

                #response = sock.recv(1024)
                #print(f'Response data: {response.decode()}')

                # print(f'Connection established {server}')
                # for line in message.split(' '):
                #    print(f'Send data: {line}')
                #    sock.send(line.encode())
                #    response = sock.recv(1024)
                #    print(f'Response data: {response.decode()}')

            print(f'Data transfer completed')
            #return response

        run_client(TCP_IP, TCP_PORT, message)


class SocketServer:
    def __init__(self, ip='localhost', port=5000) -> None:
        self.__server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server_socket.bind((ip, port))
        self.__server_socket.listen(10)

        print(f'Start echo server {self.__server_socket.getsockname()}')

    def serve_forever(self):
        def handle(sock: socket.socket, address: str):
            print(f'Connection established {address}')

            self.client = pymongo.MongoClient("mongodb://mongo_db:27017/")
            self.db = self.client["messages_db"]
            self.messages = self.db["messages"]

            while True:
                received = sock.recv(1024)
                if not received:
                    break

                data = received.decode()
                json_data = json.loads(data.replace("'", "\""))
                self.messages.insert_one(json_data)

                #sock.send(received)
                #print(f'Data send: {received}')

            self.client.close()

            print(f'Socket connection closed {address}')

            sock.close()

        with futures.ThreadPoolExecutor(10) as client_pool:
            try:
                while True:
                    new_sock, address = self.__server_socket.accept()
                    #handle(new_sock, address)
                    client_pool.submit(handle, new_sock, address)
            except Exception as e:
                print(e)
            finally:
                print('Socket server is destroyed')

    def server_close(self):
        self.__server_socket.close()


def http_server_start():
    http = HTTPServer(('', 3000), HttpHandler)
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
