#!/usr/bin/env python3

import sys, os
sys.path.append(os.path.abspath(".."))

from lib.db_op import DBOperator, GPS, Experiment, APTCPInfo
from lib.wpa_supplicant import AssocType
from lib.tcpparser import FlowType
from sqlalchemy import func
from multiprocessing import Pool
from datetime import datetime, timezone, timedelta
from matplotlib.ticker import AutoMinorLocator
from scipy.stats import pearsonr
from decimal import Decimal
import geopy
import geopy.distance
from geopy.distance import distance as geo_distance
import functools
import csv
import numpy as np
import gpxpy
import gpxpy.gpx

DB_USER = "root"
DB_PSW = "upmc75005"
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_NAME = "carfi_oldmacau"

start_t = float(sys.argv[1])
end_t = float(sys.argv[2])

db = DBOperator(DB_USER, DB_PSW, DB_HOST, DB_PORT, DB_NAME)
db_session = db.get_session()

points = db_session.query(GPS.latitude, GPS.longitude).filter(GPS.time >= start_t, GPS.time <= end_t).order_by(GPS.time).all()

def gps_dist(points):
    dist = 0
    for p1, p2 in zip(points[:-1], points[1:]):
        dist += geo_distance(p1, p2).km
    print(dist)

gps_dist(points)
