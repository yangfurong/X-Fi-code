#!/usr/bin/env python3

# This script is used to pick some special spots in Paris where we had very good, moderate or very poor performance

from lib.db_op import DBOperator, GPS, Experiment, APTCPInfo
from lib.wpa_supplicant import AssocType
from lib.tcpparser import FlowType
from sqlalchemy import func
from multiprocessing import Pool
from datetime import datetime, timezone, timedelta
from matplotlib.ticker import AutoMinorLocator
from scipy.stats import pearsonr
from decimal import Decimal
import functools
import csv
import numpy as np
import gpxpy
import gpxpy.gpx
import matplotlib
import matplotlib.style
matplotlib.use("PDF")
import matplotlib.pyplot as plt
import argparse, os
DB_USER = "root"
DB_PSW = "upmc75005"
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_NAME = "carfi_paris"

def _create_gps_trace():
    gps_trace = gpxpy.gpx.GPX()
    gps_trace.tracks.append(gpxpy.gpx.GPXTrack())
    return gps_trace

def _add_waypoints(gpx_trace, points):
    for p in points:
        gpx_trace.waypoints.append(gpxpy.gpx.GPXWaypoint(p.latitude, p.longitude, p.elevation, datetime.utcfromtimestamp(p.time)))


def main():
    db = DBOperator(DB_USER, DB_PSW, DB_HOST, DB_PORT, DB_NAME)
    session = db.get_session()
    dl_tcp = session.query(APTCPInfo.tcp_t_s, APTCPInfo.tcp_t_e, APTCPInfo.tcp_goodput_app).filter(APTCPInfo.tcp_t_s != None, APTCPInfo.tcp_direction==FlowType.DOWNLOAD).all()

    dl_tcp = sorted(dl_tcp, key=lambda x:x.tcp_goodput_app)

    max_5 = dl_tcp[-5:]
    min_5 = dl_tcp[:5]
    median_5 = dl_tcp[len(dl_tcp)//2-2:len(dl_tcp)//2+3]

    max_gpx = _create_gps_trace()
    min_gpx = _create_gps_trace()
    median_gpx = _create_gps_trace()

    all_info = [(max_5, max_gpx, "max.gpx"), (min_5, min_gpx, "min.gpx"), (median_5, median_gpx, "median.gpx")]

    for info in all_info:
        tcp_info = info[0]
        gpx_inst = info[1]
        with open(info[2], "w") as gpx_file:
            print("group: {}".format(info[2]))
            for dl in tcp_info:
                print(dl.tcp_goodput_app)
                gps_pts = session.query(GPS).filter(GPS.time >= dl.tcp_t_s, GPS.time <= dl.tcp_t_e).order_by(GPS.time).all()
                _add_waypoints(gpx_inst, [gps_pts[len(gps_pts)//2]])
            gpx_file.write(gpx_inst.to_xml())

main()
