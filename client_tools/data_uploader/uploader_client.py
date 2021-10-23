#!/usr/bin/env python3
import socket, struct
import os
import hashlib
import time
import traceback
import logging
import signal
import argparse
logging.basicConfig(level=logging.INFO)

MSG_HDR_LEN = 4

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--interface", required=True, help="the interface used for data uploading")
parser.add_argument("-s", "--server_ip", required=True, help="uploader server's IP address")
parser.add_argument("-p", "--server_port", required=True, type=int, help="uploader server's IP port")
parser.add_argument("--tar_dir", required=True, help="the folder used for keeping tarballs which are pending for uploading")
parser.add_argument("--scan_period", default=600, type=int, help="the time gap between two consecutive folder scannings")
args = parser.parse_args()

class UploaderClient(object):

    """
    Periodically scan tar_dir and upload tarballs to server
    """
    def __init__(self, intf, addr, port, tar_dir, scan_period):
        self._intf = intf
        self._addr = addr
        self._port = port
        self._tar_dir = tar_dir
        self._scan_period = scan_period
        logging.info("UploaderClient: intf {}, addr {}, port {}, tar_dir {}, scan_period {}".format(self._intf, self._addr, self._port, self._tar_dir, self._scan_period))

    def _create_client_socket(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, (self._intf + "\0").encode("utf-8"))
        self._socket.connect((self._addr, self._port))

    def _recv_msg(self, length):
        msg = b''
        while length != 0:
            tmp = self._socket.recv(length)
            msg += tmp
            length -= len(tmp)
        return msg

    def _recv_msg_hdr(self):
        return struct.unpack("!i", self._recv_msg(MSG_HDR_LEN))[0]

    def _send_msg(self, msg):
        return self._socket.sendall(msg)

    def _upload(self, tar_name):
        try:
            self._tar_file = None
            self._create_client_socket()
            self._local_md5 = hashlib.md5()

            #send file name
            msg = tar_name.encode("utf-8")
            self._send_msg(struct.pack("!i", len(msg)))
            self._send_msg(msg)

            #send content
            tar_path = os.path.join(self._tar_dir, tar_name)
            tar_fs = os.path.getsize(tar_path)
            tar_file = open(tar_path, "rb")
            self._tar_file = tar_file
            self._send_msg(struct.pack("!i", tar_fs))
            while tar_fs > 0:
                chunk_size = 4096 if tar_fs > 4096 else tar_fs
                chunk = tar_file.read(chunk_size)
                self._send_msg(chunk)
                self._local_md5.update(chunk)
                tar_fs -= len(chunk)

            #send digest
            local_digest = self._local_md5.hexdigest()
            msg = local_digest.encode("utf-8")
            self._send_msg(struct.pack("!i", len(msg)))
            self._send_msg(msg)

            #recv digest
            msg_len = self._recv_msg_hdr()
            peer_digest = self._recv_msg(msg_len).decode("utf-8")

            if local_digest == peer_digest:
                logging.info("{} is uploaded successfully".format(tar_name))
                os.system("rm -rf {}".format(tar_path))
            else:
                logging.info("digest of {} is changed".format(tar_name))
        except Exception as e:
            logging.info("{} uploading is failed.".format(tar_name))
            logging.info(traceback.format_exc())
        finally:
            if self._tar_file:
                self._tar_file.close()
            self._socket.close()

    def start(self):
        while True:
            for tarball in os.listdir(self._tar_dir):
                if tarball.endswith("tar.gz"):
                    self._upload(tarball)
            time.sleep(self._scan_period)

def sig_handler(sig, frm):
    exit(0)

def main():
    if os.path.isdir(args.tar_dir) == False:
        os.system("mkdir -p {}".format(args.tar_dir))
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    uploader_cli = UploaderClient(args.interface, args.server_ip, args.server_port, args.tar_dir, args.scan_period)
    uploader_cli.start()

if __name__ == "__main__":
    main()
