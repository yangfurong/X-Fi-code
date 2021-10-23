#!/usr/bin/env python3
from lib.db_op import DBOperator, GPS, Experiment, APTCPInfo, Link
from lib.wpa_supplicant import AssocType
from lib.tcpparser import FlowType
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from scipy.stats import pearsonr
from decimal import Decimal
import functools
import csv
import numpy as np
import gpxpy
import gpxpy.gpx
import argparse, os
import geopy
import geopy.distance
import logging
from geopy.distance import distance as geo_distance

logging.basicConfig(level=logging.INFO)

DB_USER = "root"
DB_PSW = "upmc75005"
DB_HOST = "127.0.0.1"
DB_PORT = 3306

DB_INPUT = "carfi_macau2macau"
DB_OUTPUT = "carfi_macau_merged"


def main():
    db_input = DBOperator(DB_USER, DB_PSW, DB_HOST, DB_PORT, DB_INPUT)
    db_output = DBOperator(DB_USER, DB_PSW, DB_HOST, DB_PORT, DB_OUTPUT)

    input_session = db_input.get_session()
    output_session = db_output.get_session()
    #find the latest experiment from the output database
    #latest_ts = output_session.query(func.max(Experiment.start_time)).scalar()
    #if latest_ts == None:
    #    latest_ts = 0
    latest_ts = 0
    i_exps = input_session.query(Experiment).filter(Experiment.start_time > latest_ts).all()
    #select all experiments after the latest experiment from original database
    for i_exp in i_exps:
        gps_points = input_session.query(GPS).filter(GPS.time >= i_exp.start_time, GPS.time <= i_exp.end_time).all()
        if True:
            if True:
                logging.info("find a experiment. {}".format(i_exp.id))
                aptcp_infos = input_session.query(APTCPInfo).filter(APTCPInfo.l2_conn_t_s >= i_exp.start_time, APTCPInfo.l2_conn_t_s <= i_exp.end_time).all()
                link_infos = input_session.query(Link).filter(Link.time >= i_exp.start_time, Link.time <= i_exp.end_time).all()
                link_infos = [Link(time=x.time, signal=x.signal, interface=x.interface) for x in link_infos]
                db_output.save([Experiment(start_time=i_exp.start_time, end_time=i_exp.end_time)], [GPS(latitude=x.latitude, longitude=x.longitude, elevation=x.elevation, time=x.time) for x in gps_points], [APTCPInfo(interface=x.interface, avg_speed=x.avg_speed, dist_km=x.dist_km, l2_essid=x.l2_essid, l2_bssid=x.l2_bssid, l2_freq=x.l2_freq, l2_signal_lv=x.l2_signal_lv, l2_avg_signal=x.l2_avg_signal, l2_stderr_signal=x.l2_stderr_signal, l2_assoc_type=x.l2_assoc_type, l2_auth_t_s=x.l2_auth_t_s,
                    l2_auth_t_e=x.l2_auth_t_e, l2_assoc_t_s=x.l2_assoc_t_s, l2_assoc_t_e=x.l2_assoc_t_e, l2_hs_t_s=x.l2_hs_t_s, l2_hs_t_e=x.l2_hs_t_e, l2_conn_t_s=x.l2_conn_t_s, l2_conn_t_e=x.l2_conn_t_e, l3_dhcp_t_s=x.l3_dhcp_t_s, l3_dhcp_t_e=x.l3_dhcp_t_e, l3_ip_t_s=x.l3_ip_t_s, l3_ip_t_e=x.l3_ip_t_e, l3_ip=x.l3_ip, l3_ip_prefix=x.l3_ip_prefix, l3_ip_gw=x.l3_ip_gw, l3_dhcp_server=x.l3_dhcp_server, l3_dns_servers=x.l3_dns_servers, tcp_t_s=x.tcp_t_s, tcp_t_e=x.tcp_t_e, tcp_direction=x.tcp_direction, tcp_cc=x.tcp_cc,
                    tcp_flow_nb=x.tcp_flow_nb, tcp_flows=x.tcp_flows, tcp_total_bytes_app=x.tcp_total_bytes_app, tcp_total_bytes_pcap=x.tcp_total_bytes_pcap, tcp_goodput_app=x.tcp_goodput_app, tcp_goodput_pcap=x.tcp_goodput_pcap, tcp_test_local_id=x.tcp_test_local_id) for x in aptcp_infos], [], link_infos)

if __name__ == "__main__":
    main()
