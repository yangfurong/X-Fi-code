#!/usr/bin/env python3
import socket
import threading
import struct
import hashlib
import logging
import traceback
import argparse
import signal
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uploader")
logger.setLevel(logging.INFO)

MSG_HDR_LEN = 4

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", required=True, type=int, help="uploader server's port number")
parser.add_argument("--recv_dir", required=True, help="where to store file which is been receiving")
parser.add_argument("--tar_dir", required=True, help="where to store file which is received successfully")
args = parser.parse_args()

class ClientProcessor(threading.Thread):

    def __init__(self, cli_socket, recv_dir, tar_dir):
        super().__init__()
        self._cli_socket = cli_socket
        self._recv_dir = recv_dir
        self._tar_dir = tar_dir

    def _recv_msg_hdr(self):
        msg = self._recv_msg(MSG_HDR_LEN)
        return struct.unpack("!i", msg)[0]

    def _recv_msg(self, length):
        msg = b''
        while length != 0:
            tmp = self._cli_socket.recv(length)
            length -= len(tmp)
            msg += tmp
        return msg

    def _send_msg(self, msg):
        return self._cli_socket.sendall(msg)

    def run(self):
        try:
            self._tar_file = None
            #recv file name
            self._local_md5 = hashlib.md5()
            msg_len = self._recv_msg_hdr()
            file_name = self._recv_msg(msg_len).decode("utf-8")
            file_path = os.path.join(self._recv_dir, file_name)

            tar_file = open(file_path, "wb")
            self._tar_file = tar_file

            #recv content
            msg_len = self._recv_msg_hdr()
            while msg_len > 0:
                chunk_size = 4096 if msg_len > 4096 else msg_len
                chunk = self._recv_msg(chunk_size)
                msg_len -= chunk_size
                tar_file.write(chunk)
                self._local_md5.update(chunk)

            tar_file.flush()
            #recv hex digest
            msg_len = self._recv_msg_hdr()
            peer_digest = self._recv_msg(msg_len).decode("utf-8")

            local_digest = self._local_md5.hexdigest()
            msg = local_digest.encode("utf-8")

            #if it is good, move file to tar_dir
            if peer_digest == local_digest:
                #move tarfile to tar_dir
                os.system("mv {} {}".format(file_path, self._tar_dir))
                logger.info("received integrated {}".format(file_name))
            else:
                logger.info("digest of {} is changed".format(file_name))

            #send local digest
            self._send_msg(struct.pack("!i", len(msg)))
            self._send_msg(msg)
        except Exception as e:
            logger.info(traceback.format_exc())
        finally:
            #close tarfile
            #close socket
            if self._tar_file:
                self._tar_file.close()
            self._cli_socket.close()

class UploaderServer(object):

    def __init__(self, port, recv_dir, tar_dir):
        self._port = port
        self._recv_dir = recv_dir
        self._tar_dir = tar_dir

    def _create_server_socket(self):
        self._sv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sv_socket.bind(("", self._port))
        self._sv_socket.listen(10)
        #reuse addr
        self._sv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #keepalive
        self._sv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    def start(self):
        self._create_server_socket()
        while True:
            cli_sock, addr = self._sv_socket.accept()
            cli_thread = ClientProcessor(cli_sock, self._recv_dir, self._tar_dir)
            cli_thread.start()

def sig_handler(signo, frm):
    exit(0)

if __name__ == "__main__":
    if not os.path.isdir(args.recv_dir):
        os.system("mkdir -p {}".format(args.recv_dir))
    if not os.path.isdir(args.tar_dir):
        os.system("mkdir -p {}".format(args.tar_dir))

    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    server = UploaderServer(args.port, args.recv_dir, args.tar_dir)
    server.start()
