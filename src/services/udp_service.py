class UDPService:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = self.create_socket()

    def create_socket(self):
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        return sock

    def send_message(self, message, address):
        self.socket.sendto(message.encode(), address)

    def receive_message(self):
        data, addr = self.socket.recvfrom(1024)
        return data.decode(), addr

    def close(self):
        self.socket.close()