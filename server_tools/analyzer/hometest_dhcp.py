#!/usr/bin/env python3

# This script is used to generate the general plots

from lib.db_op import DBOperator, GPS, Experiment, APTCPInfo
from lib.wpa_supplicant import AssocType
from lib.tcpparser import FlowType
from sqlalchemy import func, distinct
from multiprocessing import Pool
from datetime import datetime, timezone, timedelta
from scipy.stats import pearsonr
from decimal import Decimal
import functools
import csv
import numpy as np
import gpxpy
import gpxpy.gpx
import argparse, os


DB_USER = "root"
DB_PSW = "upmc75005"
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_NAME = "carfi_homerand_paris"

db = DBOperator(DB_USER, DB_PSW, DB_HOST, DB_PORT, DB_NAME)

session = db.get_session()

bssid_list = session.query(distinct(APTCPInfo.l2_bssid)).all()
print(bssid_list)

with open("dhcpap.csv", "w") as f:
    csv_f = csv.writer(f)
    for bssid in bssid_list:
        bssid = bssid[0]
        dhcp_success = session.query(APTCPInfo).filter(APTCPInfo.l3_ip != None, APTCPInfo.l2_bssid == bssid).count()
        total = session.query(APTCPInfo).filter(APTCPInfo.l2_bssid == bssid).count()
        freq = session.query(distinct(APTCPInfo.l2_freq)).filter(APTCPInfo.l2_bssid == bssid).one()
        avg_sig = session.query(func.avg(APTCPInfo.l2_avg_signal)).filter(APTCPInfo.l2_bssid == bssid).scalar()
        csv_f.writerow([bssid, dhcp_success, total, dhcp_success/total, freq, avg_sig])

