#!/usr/bin/env python3

# This script is used to generate the general plots
from lib.db_op import DBOperator, GPS, Experiment, APTCPInfo, CarFiScanAP
from lib.wpa_supplicant import AssocType
from lib.tcpparser import FlowType
from sqlalchemy import func, distinct, or_
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import functools
import numpy as numpy
import matplotlib.pyplot as plt
import argparse, os
import geopy.distance
import logging
import json
from geopy.distance import distance as geo_distance

FIG_FMT = "png"
FIG_EXT = ".png"

DB_USER = "root"
DB_PSW = "upmc75005"
DB_HOST = "127.0.0.1"
DB_PORT = 3306

MAX_CONN_LEN = 600 # filter all connections lasting longer than 600secs, because they were produced by occassions.

SSID_DICT = {"carfi_bologna":["%WOW FI - FASTWEB%", "%EmiliaRomagnaWiFi wifiprivacy.it%", "%ALMAWIFI%"], "carfi_paris":["%FreeWifi_secure%"], "carfi_la":["%SpectrumWiFi Plus%", "%CableWiFi%", "%TWCWiFi-Passpoint%", "%eduroam%"], "carfi_macau":["%CTM-WIFI-AUTO%"]}

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-j", "--json", required=True, help="GeoJSON file path")
parser.add_argument("-o", "--output", default="output.json", help="GeoJSON file with encoded color data")
parser.add_argument("-d", "--dbname", required=True, help="DB name")
args = parser.parse_args()

def get_coord_list_for_ap(session):
    distinct_aps = []
    min_time, max_time = None, None
    for ssid in SSID_DICT[args.dbname]:
        temp = session.query(distinct(CarFiScanAP.bssid), func.min(CarFiScanAP.time)).filter(CarFiScanAP.ssid.like(ssid)).group_by(CarFiScanAP.bssid).all()
        if temp != None:
            distinct_aps += temp
            print(temp[0])
    print(len(distinct_aps))
    distinct_aps = sorted(distinct_aps, key=lambda x:x[1])
    min_time = distinct_aps[0][1]
    max_time = distinct_aps[-1][1]
    gps_by_time = session.query(GPS).filter(GPS.time >= min_time, GPS.time <= max_time).order_by(GPS.time).all()
    gps_idx = 0
    ap_coord_list = []
    for ap in distinct_aps:
        while (gps_by_time[gps_idx].time - ap[1]) < -1:
            gps_idx += 1
        if abs(gps_by_time[gps_idx].time - ap[1]) < 1:
            ap_coord_list.append(gps_by_time[gps_idx])
        else:
            print("no associated GPS point")
    print(len(ap_coord_list))
    return ap_coord_list
    
def get_coord_list(session):
    ap_infos = session.query(APTCPInfo.l2_conn_t_s, APTCPInfo.l2_conn_t_e).filter((APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s) <= MAX_CONN_LEN).all()
    ap_coord_list = []
    for ap in ap_infos:
        gps_pts = session.query(GPS).filter(GPS.time >= ap.l2_conn_t_s, GPS.time <= ap.l2_conn_t_e).order_by(GPS.time).all()
        #omit all associations without GPS tracks
        if len(gps_pts) > 0:
            ap_coord_list.append(gps_pts[len(gps_pts)//2])
    #logging.info(f"{len(ap_coord_list)} associations are founded!")
    return ap_coord_list

#return (min_lat, max_lat, min_lon, max_lon)
def get_latlon_borders(feature):
    coords = feature["geometry"]["coordinates"]
    try:
        assert len(coords) == 1 #square
        assert len(coords[0]) == 5
    except:
        print(feature)
        raise
    lats = [float(x[1]) for x in coords[0]]
    lons = [float(x[0]) for x in coords[0]]
    return [min(lats), max(lats), min(lons), max(lons)]


def generate_data_grid(geo_json_path, coord_lst):
    with open(geo_json_path, "r") as f:
        geo_json = json.load(f)
        max_count = 0
        for coord in coord_lst:
            for feature in geo_json["features"]:
                if "assoc_count" not in feature["properties"]:
                    feature["properties"]["borders"] = get_latlon_borders(feature)
                    feature["properties"]["assoc_count"] = 0
                min_lat, max_lat, min_lon, max_lon = feature["properties"]["borders"]
                #put it into the first square in which it is located
                if min_lat <= coord.latitude <= max_lat and min_lon <= coord.longitude <= max_lon:
                    feature["properties"]["assoc_count"] += 1
                    if feature["properties"]["assoc_count"] > max_count:
                        max_count = feature["properties"]["assoc_count"]
                    break
        geo_json["max_assoc_count"] = max_count
        return geo_json

def check_integrity_of_grid(geo_json_path):
    with open(geo_json_path, "r") as f:
        geo_json = json.load(f)
        max_count = 0
        for feature in geo_json["features"]:
            if "assoc_count" in feature["properties"]:
                max_count += feature["properties"]["assoc_count"]
        print(max_count)

def main():
    db = DBOperator(DB_USER, DB_PSW, DB_HOST, DB_PORT, args.dbname)
    lst = get_coord_list_for_ap(db.get_session())
    #lst = get_coord_list(db.get_session())
    encoded_json = generate_data_grid(args.json, lst)
    with open(args.output, "w") as f:
        json.dump(encoded_json, f)

if __name__ == "__main__":
    #main()
    check_integrity_of_grid(args.json)