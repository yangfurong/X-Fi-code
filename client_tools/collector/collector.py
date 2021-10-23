#!/usr/bin/env python3
#-*- coding: utf-8 -*-
import os, shlex, sys
import json
import logging
import signal
import argparse
import time
from subprocess import Popen
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--carfi_dir", required=True, help="root dir of carfi")
parser.add_argument("-d", "--data_dir", required=True, help="data dir")
parser.add_argument("-t", "--tar_dir", required=True, help="dir for tarball of compressed data")
parser.add_argument("-l", "--location", required=True, help="location marker to indicate where the data are come from")
args = parser.parse_args()

class Collector(object):

    def __init__(self, *, carfi_dir=None, data_dir=None, tar_dir=None, loc=None):
        assert os.path.isdir(carfi_dir)
        assert os.path.isdir(data_dir)
        assert os.path.isdir(tar_dir)

        configs = None
        with open(os.path.join(carfi_dir, "carfi.json"), "r") as f:
            configs = json.load(f)

        data_dir = os.path.abspath(data_dir)
        carfi_dir = os.path.abspath(carfi_dir)
        tar_dir = os.path.abspath(tar_dir)

        self._gps_run = configs["gps"]["run"]
        self._gps_bin_cmd = "{} {} {} {}".format(configs["gps"]["bin"], configs["gps"]["args"], configs["gps"]["data_dir_option"], os.path.join(data_dir, "gps.log"))
        self._wpa_run = configs["wpa_supplicant"]["run"]
        self._wpa_bin_cmd = "{} {} {} {}".format(configs["wpa_supplicant"]["bin"], configs["wpa_supplicant"]["args"], configs["wpa_supplicant"]["data_dir_option"], os.path.join(data_dir, "wpa_supplicant.log"))

        self._roam_run = configs["roamingd"]["run"]
        self._roam_bin_cmd = "{} {} {} {}".format(configs["roamingd"]["bin"],  configs["roamingd"]["args"], configs["roamingd"]["data_dir_option"], os.path.join(data_dir, "roamingd.log"))

        self._scan_run = configs["scanner"]["run"]
        self._scan_bin_cmd = "{} {} {} {}".format(configs["scanner"]["bin"],  configs["scanner"]["args"], configs["scanner"]["data_dir_option"], os.path.join(data_dir, "scanner.log"))

        tester_data_dir = os.path.join(data_dir, "tester.data")
        assert not os.path.isdir(tester_data_dir)
        os.mkdir(tester_data_dir)
        self._tester_run = configs["tester"]["run"]
        self._tester_bin_cmd = "{} {} {} {}".format(configs["tester"]["bin"], configs["tester"]["args"], configs["tester"]["data_dir_option"], tester_data_dir)

        self._linkmon_run = configs["link_monitor"]["run"]
        self._linkmon_cmd = "{} {} {} {}".format(configs["link_monitor"]["bin"], configs["link_monitor"]["args"], configs["link_monitor"]["data_dir_option"], os.path.join(data_dir, "linkmon.log"))

        self._carfi_dir = carfi_dir
        self._data_dir = data_dir
        self._tar_dir = tar_dir
        self._loc = loc
        self._running = False

    def start(self):

        self._popens = []

        _gps_bin_cmd = shlex.split(self._gps_bin_cmd)
        _wpa_bin_cmd = shlex.split(self._wpa_bin_cmd)
        _roam_bin_cmd = shlex.split(self._roam_bin_cmd)
        _scan_bin_cmd = shlex.split(self._scan_bin_cmd)
        _tester_bin_cmd = shlex.split(self._tester_bin_cmd)
        _linkmon_cmd = shlex.split(self._linkmon_cmd)

        logging.info(_gps_bin_cmd)
        logging.info(_wpa_bin_cmd)
        logging.info(_roam_bin_cmd)
        logging.info(_scan_bin_cmd)
        logging.info(_tester_bin_cmd)
        logging.info(_linkmon_cmd)

        self._running = True
        #give gpsd minor priority to start firstly
        if self._gps_run:
            self._popens.append(Popen(_gps_bin_cmd, cwd=self._carfi_dir, stdin=None, stdout=None, stderr=None, start_new_session=True))

        if self._scan_run:
            self._popens.append(Popen(_scan_bin_cmd, cwd=self._carfi_dir, stdin=None, stdout=None, stderr=None, start_new_session=True))

        if self._tester_run:
            self._popens.append(Popen(_tester_bin_cmd, cwd=self._carfi_dir, stdin=None, stdout=None, stderr=None, start_new_session=True))

        if self._linkmon_run:
            self._popens.append(Popen(_linkmon_cmd, cwd=self._carfi_dir, stdin=None, stdout=None, stderr=None, start_new_session=True))

        if self._roam_run:
            self._popens.append(Popen(_roam_bin_cmd, cwd=self._carfi_dir, stdin=None, stdout=None, stderr=None, start_new_session=True))

        if self._wpa_run:
            self._popens.append(Popen(_wpa_bin_cmd, cwd=self._carfi_dir, stdin=None, stdout=None, stderr=None, start_new_session=True))

        self._start_time = datetime.now(timezone.utc)

    def stop(self):
        self._running = False
        #to be sure about that wpa will end firstly
        for p in reversed(self._popens):
            os.killpg(p.pid, signal.SIGTERM)
            p.wait()

        self._end_time = datetime.now(timezone.utc)
        time_fmt = "{:%Y_%m_%d_%Hh%Mm%Ss%z}"
        #NOTE: tarball naming schema: {location marker}-{start time}-{end time}.tar.gz,
        #e.g. Paris-2000_07_01_12h12m12s+0000-2001_07_01_12h12m12s+0000.tar.gz
        tarball = "{}-{}-{}.tar.gz".format(self._loc, time_fmt.format(self._start_time), time_fmt.format(self._end_time))
        cwd, name = os.path.split(self._data_dir)
        os.system("tar -zcvf {} -C {} {} > /dev/null".format(tarball, cwd, name))
        os.system("mv {} {}".format(tarball, self._tar_dir))
        #remove all data from data_dir
        os.system("rm -rf {}".format(os.path.join(self._data_dir, "*")))
        logging.info("compressed data: {}/{}".format(self._tar_dir, os.path.basename(tarball)))

    def wait_to_finish(self):
        while True:
            time.sleep(3600)

    def is_running(self):
        return self._running

carfi_collector = Collector(carfi_dir=args.carfi_dir, data_dir=args.data_dir, tar_dir=args.tar_dir, loc=args.location)

def sighandler(signum, frm):
    if carfi_collector.is_running():
        carfi_collector.stop()
    exit(0)

def run():
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    carfi_collector.start()
    carfi_collector.wait_to_finish()

if __name__ == "__main__":
    run()
