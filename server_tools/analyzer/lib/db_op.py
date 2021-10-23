#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sqlalchemy import Column, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import Integer, Numeric, String, Text, Enum, PickleType, BigInteger
from .tcpparser import FlowType
from .wpa_supplicant import AssocType
from .scan_parser import WiFiVersion
import mysql.connector

_Base = declarative_base()

class Link(_Base):
    __tablename__ = "Link"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    time = Column(Numeric(precision=64, scale=10))
    signal = Column(Numeric(precision=64, scale=10))
    interface = Column(String(32))

class ScanAP(_Base):
    __tablename__ = "ScanAP"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    time = Column(Numeric(precision=64, scale=10))
    ssid = Column(String(64))
    channel = Column(Integer)
    freq = Column(Integer)
    bssid = Column(String(64))
    rates = Column(PickleType)
    e_rates = Column(PickleType)
    signal = Column(Numeric(precision=64, scale=10))
    wifi_version = Column(Enum(WiFiVersion))

class CarFiScanAP(_Base):
    __tablename__ = "CarFiScanAP"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    time = Column(Numeric(precision=64, scale=10))
    interface = Column(String(32))
    ssid = Column(String(128))
    freq = Column(Integer)
    bssid = Column(String(64))
    signal = Column(Numeric(precision=64, scale=10))
    wifi_version = Column(Enum(WiFiVersion))

class GPS(_Base):
    __tablename__ = "GPS"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    latitude = Column(Numeric(precision=64, scale=10))
    longitude = Column(Numeric(precision=64, scale=10))
    elevation = Column(Numeric(precision=64, scale=10))
    time = Column(Numeric(precision=64, scale=10))

class Experiment(_Base):
    __tablename__ = "Experiment"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    start_time =  Column(Numeric(precision=64, scale=10))
    end_time = Column(Numeric(precision=64, scale=10))

class APTCPInfo(_Base):
    __tablename__ = "APTCPInfo"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    #Interface Info
    interface = Column(String(32))
    #Average driving Speed in km/h
    avg_speed = Column(Numeric(precision=64, scale=10))
    #covered distance
    dist_km = Column(Numeric(precision=64, scale=10))
    #WPA Info
    l2_avg_signal = Column(Numeric(precision=64, scale=10))
    l2_stderr_signal = Column(Numeric(precision=64, scale=10))
    l2_essid = Column(String(128))
    l2_bssid = Column(String(128))
    l2_freq = Column(Integer)
    l2_signal_lv = Column(Numeric(precision=64, scale=10))
    l2_assoc_type = Column(Enum(AssocType))
    l2_auth_t_s = Column(Numeric(precision=64, scale=10))
    l2_auth_t_e = Column(Numeric(precision=64, scale=10))
    l2_assoc_t_s = Column(Numeric(precision=64, scale=10))
    l2_assoc_t_e = Column(Numeric(precision=64, scale=10))
    l2_hs_t_s = Column(Numeric(precision=64, scale=10))
    l2_hs_t_e = Column(Numeric(precision=64, scale=10))
    l2_conn_t_s = Column(Numeric(precision=64, scale=10))
    l2_conn_t_e = Column(Numeric(precision=64, scale=10))
    #Roamingd Info
    l3_dhcp_t_s = Column(Numeric(precision=64, scale=10))
    l3_dhcp_t_e = Column(Numeric(precision=64, scale=10))
    l3_ip_t_s = Column(Numeric(precision=64, scale=10))
    l3_ip_t_e = Column(Numeric(precision=64, scale=10))
    l3_ip = Column(String(32))
    l3_ip_prefix = Column(Integer)
    l3_ip_gw = Column(String(32))
    l3_dhcp_server = Column(String(32))
    l3_dns_servers = Column(PickleType)
    #TCP Info
    tcp_t_s = Column(Numeric(precision=64, scale=10))
    tcp_t_e = Column(Numeric(precision=64, scale=10))
    tcp_t_s_pcap = Column(Numeric(precision=64, scale=10))
    tcp_t_e_pcap = Column(Numeric(precision=64, scale=10))
    tcp_direction = Column(Enum(FlowType))
    tcp_cc = Column(String(32))
    tcp_flow_nb = Column(Integer)
    tcp_flows = Column(PickleType)
    tcp_total_bytes_app = Column(BigInteger)
    tcp_total_bytes_pcap = Column(BigInteger)
    tcp_goodput_app = Column(Numeric(precision=64, scale=10))
    tcp_goodput_pcap = Column(Numeric(precision=64, scale=10))
    tcp_total_pkts = Column(Numeric(precision=64, scale=10))
    tcp_rxmt_pkts = Column(Numeric(precision=64, scale=10))
    tcp_loss_rate = Column(Numeric(precision=64, scale=10))
    #in order to find where the pcap is
    tcp_test_local_id = Column(Integer)

class DBOperator(object):

    def __init__(self, db_user, db_psw, db_address, db_port, db_name):
        self.engine = create_engine('mysql+mysqlconnector://{}:{}@{}:{}/{}'.format(db_user, db_psw, db_address, db_port, db_name))
        _Base.metadata.create_all(self.engine)
        self.DBSession = sessionmaker(bind=self.engine)

    def save_scans(self, exp_infos, gps_infos, ap_tcp_infos, scan_infos, link_infos, wpa_scan_infos):
        session = self.DBSession()
        session.add_all(exp_infos)
        session.add_all(gps_infos)
        session.add_all(ap_tcp_infos)
        session.add_all(scan_infos)
        session.add_all(link_infos)
        session.add_all(wpa_scan_infos)
        session.commit()
        session.close()

    def save(self, exp_infos, gps_infos, ap_tcp_infos, scan_infos, link_infos):
        session = self.DBSession()
        session.add_all(exp_infos)
        session.add_all(gps_infos)
        session.add_all(ap_tcp_infos)
        session.add_all(scan_infos)
        session.add_all(link_infos)
        session.commit()
        session.close()

    def get_session(self):
        return self.DBSession()
