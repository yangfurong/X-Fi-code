#!/usr/bin/env python3

# This script is used to generate the general plots
from lib.db_op import DBOperator, GPS, Experiment, APTCPInfo
from lib.wpa_supplicant import AssocType
from lib.tcpparser import FlowType
from sqlalchemy import func, distinct
from multiprocessing import Pool
from datetime import datetime, timezone, timedelta
from matplotlib.ticker import AutoMinorLocator, FormatStrFormatter
from scipy.stats import pearsonr
from decimal import Decimal
from cycler import cycler
import json
import scipy
import scipy.stats as sst
import math
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
import geopy.distance
from geopy.distance import distance as geo_distance
import seaborn as sns


FIG_FMT = "pdf"
FIG_EXT = ".pdf"
#LMP_PLOT_CYCLER = (cycler(color=['r', 'g', 'b', 'm', 'darkorange']) + cycler(ls=['-', '--', ':', '-.', '-']) + cycler(lw=[2, 3, 4, 4, 2]))
#MMP_PLOT_CYCLER = (cycler(color=['m', 'g', 'b', 'r', 'darkorange']) + cycler(ls=['-.', '--', ':', '-', '-']) + cycler(lw=[4, 3, 4, 2, 2]))
LMP_PLOT_CYCLER = (cycler(color=['r', 'g', 'b', 'darkorange', 'm']) + cycler(ls=['-', '--', ':', '-.', '-']) + cycler(lw=[2, 3, 4, 4, 2]))
MMP_PLOT_CYCLER = (cycler(color=['r', 'g', 'b', 'darkorange', 'm']) + cycler(ls=['-', '--', ':', '-.', '-']) + cycler(lw=[2, 3, 4, 4, 2]))
PLOT_CYCLER = None

def set_matplotlib_env():
    #matplotlib.style.use("seaborn-poster")
    sns.set_context("poster")
    #matplotlib.rcParams.update({"font.family": "serif"})
    # matplotlib.rcParams.update({"font.size": 18})
    # matplotlib.rcParams.update({"axes.labelsize": 22})
    # matplotlib.rcParams.update({"ytick.labelsize": 22})
    # matplotlib.rcParams.update({"xtick.labelsize": 22})
    # matplotlib.rcParams.update({"figure.figsize": (10, 3)})
    # matplotlib.rcParams.update({"legend.labelspacing": 0.05})
    # matplotlib.rcParams.update({"legend.handletextpad": 0.05})
    # matplotlib.rcParams.update({"legend.borderpad": 0.05})
    # matplotlib.rcParams.update({"legend.columnspacing": 0.05})
    # matplotlib.rcParams.update({"xtick.major.size": 5})
    # matplotlib.rcParams.update({"xtick.minor.size": 3.5})
    # matplotlib.rcParams.update({"xtick.major.width": 1})
    # matplotlib.rcParams.update({"xtick.minor.width": 1})
    # matplotlib.rcParams.update({"ytick.major.size": 5})
    # matplotlib.rcParams.update({"ytick.minor.size": 3.5})
    # matplotlib.rcParams.update({"ytick.major.width": 1})
    # matplotlib.rcParams.update({"ytick.minor.width": 1})

def set_matplotlib_env2():
    # matplotlib.rcParams.update({"font.size":25})
    # matplotlib.rcParams.update({"axes.labelsize":30})
    # matplotlib.rcParams.update({"ytick.labelsize":30})
    # matplotlib.rcParams.update({"xtick.labelsize":30})
    None

DB_USER = "root"
DB_PSW = "upmc75005"
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_NAMES = None

#DB_NAMES = {"LA(June 2018)":"carfi_oldla", "Paris(latest)":"carfi_paris", "Paris(July 2018)":"carfi_oldparis", "Macau(Jan-Apr 2019)":"carfi_oldmacau"}
#DB_NAMES = {"LA(June 2018)":"carfi_oldla", "Paris(latest)":"carfi_paris"}
#DB_NAMES = {"PureCarfiParis(latest)":"carfi_purecarfiparis"}
#DB_TIMEZONE = {"LA":-7, "Paris":+2, "Macao(Macao)":+8, "Macao(Singapore)":+8}
#DB_NAMES = {"LA":"carfi_oldla", "Macao(Macao)":"carfi_macau2macau_downtown", "Paris":"carfi_paris", "Macao(Singapore)": "carfi_macau_downtown"}
#DB_NAMES = {"Paris_SS": "carfi_cmpss_paris", "Paris_Random": "carfi_cmprand_paris2"}
#DB_NAMES = {"Paris_Rand1": "carfi_rand_paris", "Paris_Rand2": "carfi_rand_paris2", "Paris_Rand3": "carfi_rand_paris3"}
#DB_NAMES = {"Paris_Home": "carfi_homerand_paris"}
#DB_NAMES = {"Macao": "carfi_macau_merged_downtown"}
#DB_NAMES = {"LA":"carfi_oldla", "Macao":"carfi_macau_merged_downtown", "Paris":"carfi_paris"}
#DB_NAMES = {"Macao(Macao)":"carfi_macau2macau_downtown", "Macao(Singapore)": "carfi_macau_downtown", "Paris":"carfi_paris"}
#DB_NAMES = {"Macao(Macao)":"carfi_macau2macau", "Macao(Singapore)": "carfi_macau", "Paris":"carfi_paris", "Macao": "carfi_macau_merged", "LA": "carfi_oldla"}

#This is only used for diagnosis
DB_NAME_FOR_DIAGNOSIS = "carfi_oldla"

MAX_CONN_LEN = 600 # filter all connections lasting longer than 600secs, because they were produced by occassions.

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output_dir", required=True, help="the folder where results will be stored")
args = parser.parse_args()

def compute_CI(arr, confidence=0.95):
    a = 1.0 * np.array(arr)
    n = len(a)
    m, se = np.mean(a), sst.sem(a)
    h = se * (sst.t.ppf((1+confidence)/2.0, n-1))
    return m, m-h, m+h

def __calculate_avg_driving_speed(start_ts, end_ts, session):
    gps_points = session.query(GPS).filter(GPS.time >= start_ts, GPS.time <= end_ts).all()
    gps_distance = None
    for idx in range(1, len(gps_points)):
        if gps_distance == None:
            gps_distance = 0
        gps_distance += geo_distance((gps_points[idx].latitude, gps_points[idx].longitude), (gps_points[idx-1].latitude, gps_points[idx-1].longitude)).km
    if gps_distance == None:
        return None
    else:
        return gps_distance / ((float(end_ts) - float(start_ts)) / 3600)

def dataset_overview(func):
    @functools.wraps(func)
    def wrapper(session_dict, output_dir):
        for db_name, session in session_dict.items():
            with open(os.path.join(output_dir, db_name+"_dataset_overview.csv"), "w") as f:
                csv_f = csv.writer(f)
                csv_f.writerow(["total_ap_num", "ip_ap_num", "tcp_ap_num", "2.4G AP number", "5G AP number", "l2_duration", "ip_duration", "tcp_duration", "l2_distance", "ip_distance", "tcp_distance", "distinct_ap_num", "distinct_2.4G", "distinct_5G", "dates_range", "distinct_days", "new_assoc", "re_assoc"])
                csv_f.writerow(func(session))
    return wrapper

def get_all_freq_number(session):
    freq_2_4 = session.query(APTCPInfo.l2_freq).filter(APTCPInfo.l2_freq <= 2500).count()
    freq_5 = session.query(APTCPInfo.l2_freq).filter(APTCPInfo.l2_freq >= 5000).count()
    return [freq_2_4, freq_5]

def get_ip_freq_number(session):
    """
    get # of 2.4 AP and # of 5 AP from APs from which CarFi gets IP address successfully
    """
    freq_2_4 = session.query(APTCPInfo.l2_freq).filter(APTCPInfo.l3_ip != None, APTCPInfo.l2_freq <= 2500).count()
    freq_5 = session.query(APTCPInfo.l2_freq).filter(APTCPInfo.l3_ip != None, APTCPInfo.l2_freq >= 5000).count()
    return [freq_2_4, freq_5]

def get_tcp_freq_number(session):
    freq_2_4 = session.query(APTCPInfo.l2_freq).filter(APTCPInfo.tcp_t_s != None, APTCPInfo.l2_freq <= 2500).count()
    freq_5 = session.query(APTCPInfo.l2_freq).filter(APTCPInfo.tcp_t_s != None, APTCPInfo.l2_freq >= 5000).count()
    return [freq_2_4, freq_5]

def get_ap_assoc_type_dist(session):
    new = session.query(APTCPInfo).filter(APTCPInfo.l2_assoc_type == AssocType.NEW).count()
    reassoc = session.query(APTCPInfo).filter(APTCPInfo.l2_assoc_type == AssocType.REASSOC).count()
    return [new, reassoc]

def get_total_ap_num(session):
    return session.query(APTCPInfo).count()

def get_ip_ap_num(session):
    return session.query(APTCPInfo).filter(APTCPInfo.l3_ip != None).count()

def get_tcp_ap_num(session):
    return session.query(APTCPInfo).filter(APTCPInfo.tcp_t_s != None).count()

def get_l2_dist_sum(session):
    dist = session.query(func.sum(APTCPInfo.dist_km)).filter(APTCPInfo.dist_km != None).scalar()
    return dist

def get_ip_dist_sum(session):
    return session.query(func.sum(APTCPInfo.dist_km)).filter(APTCPInfo.dist_km != None, APTCPInfo.l3_ip != None).scalar()

def get_tcp_dist_sum(session):
    return session.query(func.sum(APTCPInfo.dist_km)).filter(APTCPInfo.dist_km != None, APTCPInfo.tcp_t_s != None).scalar()

def get_distinct_ap_num(session):
    return session.query(distinct(APTCPInfo.l2_bssid)).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).count()

def get_distinct_24_ap_num(session):
    return session.query(distinct(APTCPInfo.l2_bssid)).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.l2_freq <= 2500).count()

def get_distinct_5_ap_num(session):
    return session.query(distinct(APTCPInfo.l2_bssid)).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.l2_freq > 5000).count()

def get_dates(session):
    st_list = session.query(Experiment.start_time).all()
    dates_list = sorted(set(datetime.utcfromtimestamp(st.start_time).date() for st in st_list))
    dates_range = None
    if len(dates_list) > 10:
        dates_range = "{} to {}".format(dates_list[0], dates_list[-1])
    else:
        dates_range = functools.reduce(lambda x,y: str(x)+","+str(y), dates_list)
    return dates_range, len(dates_list)

def get_l2_duration_sum(session):
    secs = session.query(func.sum(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s)).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).scalar()
    if secs == None:
        return "None"
    secs = int(secs)
    hour = secs // 3600
    secs = secs % 3600
    minute = secs // 60
    secs = secs % 60
    return "{}h{}m{}s".format(hour, minute, secs)

def get_ip_duration_sum(session):
    secs = session.query(func.sum(APTCPInfo.l3_ip_t_e - APTCPInfo.l3_ip_t_s)).filter(APTCPInfo.l3_ip != None).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).scalar()
    if secs == None:
        return "None"
    secs = int(secs)
    hour = secs // 3600
    secs = secs % 3600
    minute = secs // 60
    secs = secs % 60
    return "{}h{}m{}s".format(hour, minute, secs)

def get_tcp_duration_sum(session):
    secs = session.query(func.sum(APTCPInfo.tcp_t_e - APTCPInfo.tcp_t_s)).filter(APTCPInfo.tcp_t_s != None).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).scalar()
    if secs == None:
        return "None"
    secs = int(secs)
    hour = secs // 3600
    secs = secs % 3600
    minute = secs // 60
    secs = secs % 60
    return "{}h{}m{}s".format(hour, minute, secs)


@dataset_overview
def output_dataset_overview(session):
    freq_nb_24, freq_nb_5 = get_all_freq_number(session)
    dates_range, distinct_days = get_dates(session)
    new_assoc, re_assoc = get_ap_assoc_type_dist(session)
    return get_total_ap_num(session), get_ip_ap_num(session), get_tcp_ap_num(session), freq_nb_24, freq_nb_5, get_l2_duration_sum(session), get_ip_duration_sum(session), get_tcp_duration_sum(session), get_l2_dist_sum(session), get_ip_dist_sum(session), get_tcp_dist_sum(session), get_distinct_ap_num(session), get_distinct_24_ap_num(session), get_distinct_5_ap_num(session), dates_range, distinct_days, new_assoc, re_assoc

def __cdf_to_ccdf(x, y):
    y = [1.0-temp for temp in y]
    return x, y

def __get_cdf(arr):
      arr = sorted(arr)
      #also return mean and stderr
      mean = np.mean(arr)
      std = np.std(arr)
      mmax = np.max(arr)
      mmin = np.min(arr)
      counts = []
      x = []
      for elem in arr:
          if len(counts) == 0:
              x.append(elem)
              counts.append(1)
          else:
              if elem == x[-1]:
                  counts[-1] += 1
              else:
                  counts.append(1)
                  x.append(elem)
      y = []
      for i in range(0, len(counts)):
          if i != 0:
              counts[i] += counts[i-1]
          y.append(float(counts[i])/len(arr))
      return x, y, mean, std, mmax, mmin

def __get_quantile_from_cdf(x, y, pt):
    assert 0 <= pt <= 1
    #print(x, y)
    for i in range(len(x)):
        if pt == y[i]:
            return x[i]
        #linear interpolatian
        elif pt > y[i] and pt < y[i+1]:
            return (float(x[i]) * (y[i+1] - pt) + float(x[i+1]) * (pt - y[i])) / (y[i+1] - y[i])
    return None

def __get_quantile_from_ccdf(x, y, pt):
    assert 0 <= pt <= 1
    for i in range(len(x)):
        if pt == y[i]:
            return x[i]
        elif pt < y[i] and pt > y[i+1]:
            return (float(x[i]) * (y[i+1] - pt) + float(x[i+1]) * (pt - y[i])) / (y[i+1] - y[i])
    return None

def filter_by_y(x, y, ymin=0, ymax=1):
    xn = []
    yn = []
    for xp, yp in zip(x, y):
        if ymin <= yp <= ymax:
            xn.append(xp)
            yn.append(yp)
    return xn, yn

def ccdf_plotter(plot_name, xaxis_label, yaxis_label="Frac. of assoc. ", log=False, ymin=0, ymax=1, legend_loc="upper right"):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(session_dict, output_dir):
            set_matplotlib_env()
            quantiles = {}
            plt.rc('axes', prop_cycle=PLOT_CYCLER)
            for db_name, session in sorted(session_dict.items()):
                x, y, mean, std, mmax, mmin = func(session)
                quantiles[db_name] = [__get_quantile_from_cdf(x, y, 0.25), __get_quantile_from_cdf(x, y, 0.5), __get_quantile_from_cdf(x, y, 0.75), __get_quantile_from_cdf(x, y, 0.9), mean, std, mmax, mmin]
                x, y = __cdf_to_ccdf(x, y)
                #quantiles[db_name] = [__get_quantile_from_ccdf(x, y, 0.25), __get_quantile_from_ccdf(x, y, 0.5), __get_quantile_from_ccdf(x, y, 0.75), __get_quantile_from_ccdf(x, y, 0.9)]
                x, y = filter_by_y(x, y, ymin, ymax)
                plt.plot(x, y, drawstyle="default", label=db_name)
            plt.ylim(ymin, ymax)
            plt.xlabel(xaxis_label)
            plt.ylabel(yaxis_label)
            if log:
                plt.xscale("log")
                sf = FormatStrFormatter("%.4g")
                plt.gca().xaxis.set_major_formatter(sf)
                plt.gca().yaxis.set_major_formatter(sf)
                plt.gca().yaxis.set_minor_locator(AutoMinorLocator())
                #plt.gca().xaxis.grid(which="both")
                #plt.gca().yaxis.grid(which="major")
            if not log:
                plt.gca().xaxis.set_minor_locator(AutoMinorLocator())
                plt.gca().yaxis.set_minor_locator(AutoMinorLocator())
                #plt.grid()
            plt.legend(loc=legend_loc, prop={"size":18})
            plt.savefig(os.path.join(output_dir, plot_name), format=FIG_FMT, bbox_inches="tight")
            plt.close()

            with open(os.path.join(output_dir, plot_name.split(".")[0]+".csv"), "w") as f:
                csv_f = csv.writer(f)
                csv_f.writerow(["", "0.25", "0.5", "0.75", "0.9", "mean", "std"])
                for k, v in sorted(quantiles.items()):
                    csv_f.writerow([k] + v)
        return wrapper
    return decorator

def cdf_plotter(plot_name, xaxis_label, yaxis_label="Frac. of assoc.", log=False, ymin=0, ymax=1, legend_loc="lower right"):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(session_dict, output_dir):
            set_matplotlib_env()
            quantiles = {}
            plt.rc("axes", prop_cycle=PLOT_CYCLER)
            for db_name, session in sorted(session_dict.items()):
                x, y, mean, std, mmax, mmin = func(session)
                #quantiles[db_name] = [__get_quantile_from_cdf(x, y, 0.25), __get_quantile_from_cdf(x, y, 0.5), __get_quantile_from_cdf(x, y, 0.75), __get_quantile_from_cdf(x, y, 0.8)]
                quantiles[db_name] = [__get_quantile_from_cdf(x, y, 0.25), __get_quantile_from_cdf(x, y, 0.5), __get_quantile_from_cdf(x, y, 0.75), __get_quantile_from_cdf(x, y, 0.9), mean, std, mmax, mmin]
                #This is not a good way to treat outliers (There were several super long L2 conn from LA data. Because Andrea stopped some places where WiFi is available to debug CarFi for a long period.). Because I delete outliers from DB.
                #FIXME: keep those outlier in DB. while filter outliers when generate duration plot.
                #if db_name == "LA" and plot_name == "l2_interap_time_cdf" + FIG_EXT:
                #    x, y = x[:-1], y[:-1]
                #if db_name == "LA" and plot_name == "l3_interip_time_cdf" + FIG_EXT:
                #    x, y = x[:-1], y[:-1]
                #if db_name == "LA" and plot_name == "tcp_intertcp_time_cdf" + FIG_EXT:
                #    x, y = x[:-1], y[:-1]
                x, y = filter_by_y(x, y, ymin, ymax)
                plt.plot(x, y, drawstyle="default", label=db_name)
            plt.ylim(ymin, ymax)
            plt.xlabel(xaxis_label)
            plt.ylabel(yaxis_label)
            if log:
                plt.xscale("log")
                sf = FormatStrFormatter("%.4g")
                plt.gca().xaxis.set_major_formatter(sf)
                plt.gca().yaxis.set_major_formatter(sf)
                plt.gca().yaxis.set_minor_locator(AutoMinorLocator())
                #plt.gca().xaxis.grid(which="both")
                #plt.gca().yaxis.grid(which="major")
            if not log:
                plt.gca().xaxis.set_minor_locator(AutoMinorLocator())
                plt.gca().yaxis.set_minor_locator(AutoMinorLocator())
                #plt.grid()
            plt.legend(loc=legend_loc, prop={"size":18})
            plt.savefig(os.path.join(output_dir, plot_name), format=FIG_FMT, bbox_inches="tight")
            plt.close()

            with open(os.path.join(output_dir, plot_name.split(".")[0]+".csv"), "w") as f:
                csv_f = csv.writer(f)
                csv_f.writerow(["", "0.25", "0.5", "0.75", "0.9", "mean", "std"])
                for k, v in sorted(quantiles.items()):
                    csv_f.writerow([k] + v)
        return wrapper
    return decorator

def stacked_hist_plotter(plot_name, xaxis_label=None, yaxis_label=None, ymin=0, ymax=1, legend_loc="upper right"):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(session_dict, output_dir):
            set_matplotlib_env()
            db_dict = {}
            series_arr = []
            series_std_arr = []
            series_labels = None
            xticks = []
            for db_name, session in sorted(session_dict.items()):
                y_list, labels, y_std = func(session)
                series_labels = labels
                if len(series_arr) == 0:
                    series_arr += [[] for i in labels]
                    series_std_arr += [[] for i in labels]
                for i, y in enumerate(y_list):
                    series_arr[i].append(float(y))
                if y_std:
                    for i, y in enumerate(y_std):
                        series_std_arr[i].append(float(y))
                db_dict[db_name] = [y_list, labels]
                xticks.append(db_name)
            bottom = None

            for i in range(len(series_labels)):
                k = series_labels[i]
                v = series_arr[i]
                std = series_std_arr[i]
                x = range(len(v))
                if bottom == None:
                    bottom = [0 for e in v]
                if len(std) == 0:
                    std = None
                plt.bar(x, v, bottom=bottom, label=k, yerr=std, width=0.5)
                bottom = [acc+new for acc, new in zip(bottom, v)]
            plt.xticks(x, xticks)
            plt.xlabel(xaxis_label)
            plt.ylabel(yaxis_label)
            plt.legend(prop={"size":14}, loc=legend_loc)
            plt.savefig(os.path.join(output_dir, plot_name), format=FIG_FMT, bbox_inches="tight")
            plt.close()

            with open(os.path.join(output_dir, plot_name.split(".")[0]+".csv"), "w") as f:
                csv_f = csv.writer(f)
                for k, v in sorted(db_dict.items()):
                    csv_f.writerow(["city"] + v[1])
                    csv_f.writerow([k] + v[0])
        return wrapper
    return decorator        

def get_assoc_setup_overhead_breakdown(session):
    #auth, assoc, handshake, dhcp
    res = session.query(APTCPInfo.l2_auth_t_e-APTCPInfo.l2_auth_t_s, APTCPInfo.l2_assoc_t_e-APTCPInfo.l2_assoc_t_s, APTCPInfo.l2_hs_t_e-APTCPInfo.l2_hs_t_s, APTCPInfo.l3_dhcp_t_e-APTCPInfo.l3_dhcp_t_s).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.l3_ip != None).all()
    auth = [x[0] * 100 / sum(x) for x in res]
    assoc = [x[1] * 100 / sum(x) for x in res]
    hs = [x[2] * 100 / sum(x) for x in res]
    dhcp = [x[3] * 100 / sum(x) for x in res]

    mean_auth, std_auth = np.mean(auth), np.std(auth)
    mean_assoc, std_assoc = np.mean(assoc), np.std(assoc)
    mean_hs, std_hs = np.mean(hs), np.std(hs)
    mean_dhcp, std_dhcp = np.mean(dhcp), np.std(dhcp)
    return [mean_auth, mean_assoc, mean_hs, mean_dhcp], ["AP Auth.", "AP Assoc.", "EAP/PEAP Auth.", "DHCP"], None

@stacked_hist_plotter("overhead_breakdown"+FIG_EXT, yaxis_label="% of time overhead", legend_loc="center right")
def plot_assoc_setup_overhead_breakdown(session):
    return get_assoc_setup_overhead_breakdown(session)

#get the ratio of tcp duration 
def get_ratio_of_tcp_vs_whole(session):
    #for all tcp assocations
    ratio = session.query(func.avg((APTCPInfo.tcp_t_e - APTCPInfo.tcp_t_s)/(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_auth_t_s))).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.tcp_t_s != None).one()
    return ratio[0]*100

@stacked_hist_plotter("ratio_of_tcp_vs_whole_bar"+FIG_EXT, yaxis_label="% of whole assoc. duration", legend_loc="center right")
def plot_ratio_of_tcp_vs_whole(session):
    ratio = get_ratio_of_tcp_vs_whole(session)
    return [ratio, 100-ratio], ["TCP conn.", "Conn. setup"], None

#assoc dist_km CDF
def get_ap_coverage_m_cdf(session):
    l2_cov_m = session.query(func.avg(APTCPInfo.dist_km)).filter(APTCPInfo.dist_km != None, APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).group_by(APTCPInfo.l2_bssid).all()
    #convert into meters
    l2_cov_m = (x[0] * 1000 for x in l2_cov_m)
    return __get_cdf(l2_cov_m)

@cdf_plotter("dist_meters_cdf" + FIG_EXT, "Avg. dist. of an AP (m)")
def plot_ap_coverage_m_cdf(session):
    return get_ap_coverage_m_cdf(session)

#L2 connection duration CDF
def get_l2_conn_duration_cdf(session):
    l2_conns = session.query(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    l2_conns = (x[0] for x in l2_conns)
    return __get_cdf(l2_conns)

@cdf_plotter("l2_conn_duration_cdf" + FIG_EXT, "Link-layer connectivity duration (s)", ymin=0, ymax=0.9)
def plot_l2_conn_duration_cdf(session):
    return get_l2_conn_duration_cdf(session)

@ccdf_plotter("l2_conn_duration_ccdf" + FIG_EXT, "Link-layer connectivity duration (s)", ymin=0.1, ymax=1)
def plot_l2_conn_duration_ccdf(session):
    return get_l2_conn_duration_cdf(session)

def get_l2_auth_duration_cdf(session):
    auth_durations = session.query(APTCPInfo.l2_auth_t_e - APTCPInfo.l2_auth_t_s).all()
    auth_durations = (x[0] for x in auth_durations)
    return __get_cdf(auth_durations)

@cdf_plotter("l2_auth_duration_cdf" + FIG_EXT, "L2 authentication time (s)")
def plot_l2_auth_duration_cdf(session):
    return get_l2_auth_duration_cdf(session)

def get_l2_assoc_duration_cdf(session):
    assoc_durations = session.query(APTCPInfo.l2_assoc_t_e - APTCPInfo.l2_assoc_t_s).all()
    assoc_durations = (x[0] for x in assoc_durations)
    return __get_cdf(assoc_durations)

@cdf_plotter("l2_assoc_duration_cdf" + FIG_EXT, "L2 association time (s)")
def plot_l2_assoc_duration_cdf(session):
    return get_l2_assoc_duration_cdf(session)

def get_l2_hs_duration_cdf(session):
    hs_durations = session.query(APTCPInfo.l2_hs_t_e - APTCPInfo.l2_hs_t_s).all()
    hs_durations = (x[0] for x in hs_durations)
    return __get_cdf(hs_durations)

@cdf_plotter("l2_hs_duration_cdf" + FIG_EXT, "L2 4-way handshake time (s)")
def plot_l2_hs_duration_cdf(session):
    return get_l2_hs_duration_cdf(session)


def get_l2_overall_assoc_duration_cdf(session):
    overall_assoc_ds = session.query(APTCPInfo.l2_hs_t_e - APTCPInfo.l2_auth_t_s).all()
    overall_assoc_ds = (x[0] for x in overall_assoc_ds)
    return __get_cdf(overall_assoc_ds)

@cdf_plotter("l2_overall_assoc_cdf" + FIG_EXT, "Wi-Fi association time (s)")
def plot_l2_overall_assoc_duration_cdf(session):
    return get_l2_overall_assoc_duration_cdf(session)

def get_l2_ap_signal_cdf(session):
    sigs = session.query(APTCPInfo.l2_signal_lv).filter(APTCPInfo.l2_assoc_type == AssocType.NEW).all()
    sigs = (x[0] for x in sigs)
    return __get_cdf(sigs)

@cdf_plotter("l2_ap_signal_cdf" + FIG_EXT, "ISS of associations (dBm)")
def plot_l2_ap_signal_cdf(session):
    return get_l2_ap_signal_cdf(session)

@ccdf_plotter("l2_ap_signal_ccdf" + FIG_EXT, "ISS of associations (dBm)")
def plot_l2_ap_signal_ccdf(session):
    return get_l2_ap_signal_cdf(session)

def __calculate_avg_driving_speed(start_ts, end_ts, session):
    gps_points = session.query(GPS).filter(GPS.time >= start_ts, GPS.time <= end_ts).all()
    gps_distance = None
    for idx in range(1, len(gps_points)):
        if gps_distance == None:
            gps_distance = 0
        gps_distance += geo_distance((gps_points[idx].latitude, gps_points[idx].longitude), (gps_points[idx-1].latitude, gps_points[idx-1].longitude)).km
    if gps_distance == None:
        return None
    else:
        return gps_distance / ((float(end_ts) - float(start_ts)) / 3600)

#The CDF of average speed of inter-conn periods
def get_inter_conn_avg_speed_cdf(session):
    exps = session.query(Experiment).order_by(Experiment.start_time).all()
    trips = []
    for exp in exps:
        if len(trips) !=0 and (exp.start_time - trips[-1][1]) <= 30:
            #the gap between two consecutive data collections should not exceed 30s
            trips[-1][1] = exp.end_time
        else:
            trips.append([exp.start_time, exp.end_time])
    inter_ap_avg_speeds = []
    for trip in trips:
        l2_conns = session.query(APTCPInfo.l2_conn_t_s, APTCPInfo.l2_conn_t_e).filter(trip[1] >= APTCPInfo.l2_conn_t_s, APTCPInfo.l2_conn_t_s >= trip[0]).order_by(APTCPInfo.l2_conn_t_s).all()
        l2_conn_id = 1
        while l2_conn_id < len(l2_conns):
            speed = __calculate_avg_driving_speed(l2_conns[l2_conn_id-1].l2_conn_t_e, l2_conns[l2_conn_id].l2_conn_t_s, session)
            # If there is no GPS trace, we have no way to calculate the speed. So, we will just ignore those data points.
            if speed != None:
                inter_ap_avg_speeds.append(speed)
            l2_conn_id += 1
    return __get_cdf(inter_ap_avg_speeds)

@cdf_plotter("inter_conn_avg_speed_cdf" + FIG_EXT, "Avg. speed per disconnected period (km/h)")
def plot_inter_conn_avg_speed_cdf(session):
    return get_inter_conn_avg_speed_cdf(session)

#Inter-AP duration CDF
def get_inter_ap_duration_cdf(session):
    exps = session.query(Experiment).order_by(Experiment.start_time).all()
    trips = []
    for exp in exps:
        if len(trips) !=0 and (exp.start_time - trips[-1][1]) <= 30:
            #the gap between two consecutive data collections should not exceed 30s
            trips[-1][1] = exp.end_time
        else:
            trips.append([exp.start_time, exp.end_time])

    inter_ap_durations = []

    for trip in trips:
        l2_conns = session.query(APTCPInfo.l2_conn_t_s, APTCPInfo.l2_conn_t_e).filter(trip[1] >= APTCPInfo.l2_conn_t_s, APTCPInfo.l2_conn_t_s >= trip[0]).order_by(APTCPInfo.l2_conn_t_s).all()
        l2_conn_id = 1
        while l2_conn_id < len(l2_conns):
            inter_ap_durations.append(l2_conns[l2_conn_id].l2_conn_t_s - l2_conns[l2_conn_id-1].l2_conn_t_e)
            #if inter_ap_durations[-1] <= 0.1:
            #    print(l2_conns[l2_conn_id].l2_conn_t_s, l2_conns[l2_conn_id-1].l2_conn_t_e)
            l2_conn_id += 1
    return __get_cdf(inter_ap_durations)

#Inter-IP duration CDF
def get_inter_ip_duration_cdf(session):
    exps = session.query(Experiment).order_by(Experiment.start_time).all()
    trips = []
    for exp in exps:
        if len(trips) !=0 and (exp.start_time - trips[-1][1]) <= 30:
            #the gap between two consecutive data collections should not exceed 30s
            trips[-1][1] = exp.end_time
        else:
            trips.append([exp.start_time, exp.end_time])

    inter_ip_durations = []

    for trip in trips:
        l2_conns = session.query(APTCPInfo.l3_ip_t_s, APTCPInfo.l3_ip_t_e).filter(trip[1] >= APTCPInfo.l3_ip_t_e, APTCPInfo.l3_ip_t_s >= trip[0], APTCPInfo.l3_ip != None).order_by(APTCPInfo.l3_ip_t_s).all()
        l2_conn_id = 1
        while l2_conn_id < len(l2_conns):
            inter_ip_durations.append(l2_conns[l2_conn_id].l3_ip_t_s - l2_conns[l2_conn_id-1].l3_ip_t_e)
            l2_conn_id += 1
    return __get_cdf(inter_ip_durations)

#Inter-TCP duration CDF
def get_inter_tcp_duration_cdf(session):
    exps = session.query(Experiment).order_by(Experiment.start_time).all()
    trips = []
    for exp in exps:
        if len(trips) !=0 and (exp.start_time - trips[-1][1]) <= 30:
            #the gap between two consecutive data collections should not exceed 30s
            trips[-1][1] = exp.end_time
        else:
            trips.append([exp.start_time, exp.end_time])

    inter_tcp_durations = []

    for trip in trips:
        l2_conns = session.query(APTCPInfo.tcp_t_s, APTCPInfo.tcp_t_e).filter(trip[1] >= APTCPInfo.tcp_t_e, APTCPInfo.tcp_t_s>= trip[0], APTCPInfo.tcp_t_s != None).order_by(APTCPInfo.tcp_t_s).all()
        l2_conn_id = 1
        while l2_conn_id < len(l2_conns):
            inter_tcp_durations.append(l2_conns[l2_conn_id].tcp_t_s - l2_conns[l2_conn_id-1].tcp_t_e)
            l2_conn_id += 1
    return __get_cdf(inter_tcp_durations)


@cdf_plotter("l2_interap_time_cdf" + FIG_EXT, "Duration of link-layer conn. holes (s)", "CDF", log=True)
def plot_inter_ap_duration_cdf(session):
     return get_inter_ap_duration_cdf(session)

@cdf_plotter("l3_interip_time_cdf" + FIG_EXT, "Duration of IP conn. holes (s)", "CDF", log=True)
def plot_inter_ip_duration_cdf(session):
     return get_inter_ip_duration_cdf(session)

@cdf_plotter("tcp_intertcp_time_cdf" + FIG_EXT, "Duration of TCP conn. holes (s)", "CDF", log=True)
def plot_inter_tcp_duration_cdf(session):
     return get_inter_tcp_duration_cdf(session)

#IP duration CDF
def get_ip_duration_cdf(session):
    ip_conns = session.query(APTCPInfo.l3_ip_t_e - APTCPInfo.l3_ip_t_s).filter(APTCPInfo.l3_ip != None).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    ip_conns = (x[0] for x in ip_conns)
    return __get_cdf(ip_conns)

@cdf_plotter("ip_duration_cdf" + FIG_EXT, "IP connectivity duration (s)", ymin=0, ymax=0.9)
def plot_ip_duration_cdf(session):
    return get_ip_duration_cdf(session)

@ccdf_plotter("ip_duration_ccdf" + FIG_EXT, "IP connectivity duration (s)", ymin=0.1, ymax=1)
def plot_ip_duration_ccdf(session):
    return get_ip_duration_cdf(session)

def get_until_ip_time_cdf(session):
    #to filter the artifacts in LA, which is caused by manually starting roamingd
    data = session.query(APTCPInfo.l3_ip_t_s - APTCPInfo.l2_assoc_t_s).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.l3_ip != None).filter((APTCPInfo.l3_dhcp_t_s - APTCPInfo.l2_conn_t_s) < 2).all()
    data = (x[0] for x in data)
    return __get_cdf(data)

def get_until_tcp_time_cdf(session):
    data = session.query(APTCPInfo.tcp_t_s_pcap - APTCPInfo.l2_assoc_t_s).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.tcp_t_s_pcap != None).all()
    data = (x[0] for x in data)
    return __get_cdf(data)

@cdf_plotter("until_ip_time_cdf"+FIG_EXT, "Time until IP acquisition (s)", log=True)
def plot_until_ip_time_cdf(session):
    return get_until_ip_time_cdf(session)

@cdf_plotter("until_tcp_time_cdf"+FIG_EXT, "Time until first TCP ACK (s)", log=True)
def plot_until_tcp_time_cdf(session):
    return get_until_tcp_time_cdf(session)

def get_dhcp_duration_cdf(session):
    dhcp_durations = session.query(APTCPInfo.l3_dhcp_t_e - APTCPInfo.l3_dhcp_t_s).filter(APTCPInfo.l3_ip != None).all()
    dhcp_durations = (x[0] for x in dhcp_durations)
    return __get_cdf(dhcp_durations)

@cdf_plotter("dhcp_time_cdf" + FIG_EXT, "DHCP time (s)", log=True)
def plot_dhcp_duration_cdf(session):
    return get_dhcp_duration_cdf(session)

def get_ip_to_tcp_time_cdf(session):
    #time BTWN first ack from peer and ip acquisition
    ip_to_tcp_time = session.query(APTCPInfo.tcp_t_s_pcap - APTCPInfo.l3_ip_t_s).filter(APTCPInfo.tcp_t_s_pcap != None).all()
    ip_to_tcp_time = (x[0] for x in ip_to_tcp_time)
    return __get_cdf(ip_to_tcp_time)

@cdf_plotter("ip_to_tcp_time_cdf" + FIG_EXT, "IP-to-TCP time (s)", log=True)
def plot_ip_to_tcp_time_cdf(session):
    return get_ip_to_tcp_time_cdf(session)

#TCP duration CDF
def get_tcp_duration_cdf(session):
    tcp_durations = session.query(APTCPInfo.tcp_t_e - APTCPInfo.tcp_t_s).filter(APTCPInfo.tcp_t_s != None).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    tcp_durations = (x[0] for x in tcp_durations)
    return __get_cdf(tcp_durations)

@cdf_plotter("tcp_duration_cdf" + FIG_EXT, "TCP connectivity duration (s)", ymin=0, ymax=0.9)
def plot_tcp_duration_cdf(session):
    return get_tcp_duration_cdf(session)

@ccdf_plotter("tcp_duration_ccdf" + FIG_EXT, "TCP connectivity duration (s)", ymin=0.1, ymax=1)
def plot_tcp_duration_ccdf(session):
    return get_tcp_duration_cdf(session)

def get_overall_tcp_download_goodput_cdf(session):
    tcp_infos = session.query(APTCPInfo.tcp_goodput_app).filter(APTCPInfo.tcp_t_s != None, APTCPInfo.tcp_direction==FlowType.DOWNLOAD).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    tcp_infos = (x[0] for x in tcp_infos)
    return __get_cdf(tcp_infos)

@cdf_plotter("overall_tcp_download_goodput_cdf" + FIG_EXT, "Average download goodput (Mbit/s)", log=True)
def plot_overall_tcp_download_goodput_cdf(session):
    return get_overall_tcp_download_goodput_cdf(session)

@ccdf_plotter("overall_tcp_download_goodput_ccdf" + FIG_EXT, "Average download goodput (Mbit/s)", log=True, legend_loc="lower left")
def plot_overall_tcp_download_goodput_ccdf(session):
    return get_overall_tcp_download_goodput_cdf(session)

def get_overall_tcp_upload_goodput_cdf(session):
    tcp_infos = session.query(APTCPInfo.tcp_goodput_pcap).filter(APTCPInfo.tcp_t_s != None, APTCPInfo.tcp_direction==FlowType.UPLOAD).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    tcp_infos = (x[0] for x in tcp_infos)
    return __get_cdf(tcp_infos)

@cdf_plotter("overall_tcp_upload_goodput_cdf" + FIG_EXT, "Average upload goodput (Mbit/s)", log=True)
def plot_overall_tcp_upload_goodput_cdf(session):
    return get_overall_tcp_upload_goodput_cdf(session)

@ccdf_plotter("overall_tcp_upload_goodput_ccdf" + FIG_EXT, "Average upload goodput (Mbit/s)", log=True, legend_loc="lower left")
def plot_overall_tcp_upload_goodput_ccdf(session):
    return get_overall_tcp_upload_goodput_cdf(session)

#TCP average goodput CDF
  # classify cdf by different parameter combinations
  # cc_algorithm
  # concurrency
  # upload or download
def get_tcp_avg_goodput_cdf(session):
    tcp_infos = session.query(APTCPInfo.tcp_direction, APTCPInfo.tcp_cc, APTCPInfo.tcp_flow_nb, APTCPInfo.tcp_goodput_app, APTCPInfo.tcp_goodput_pcap).filter(APTCPInfo.tcp_t_s != None).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    cdf_dict = {}
    for tcp_info in tcp_infos:
        if tcp_info.tcp_direction not in cdf_dict:
            cdf_dict[tcp_info.tcp_direction] = {}
        if tcp_info.tcp_flow_nb not in cdf_dict[tcp_info.tcp_direction]:
            cdf_dict[tcp_info.tcp_direction][tcp_info.tcp_flow_nb] = {}
        if tcp_info.tcp_cc not in cdf_dict[tcp_info.tcp_direction][tcp_info.tcp_flow_nb]:
            cdf_dict[tcp_info.tcp_direction][tcp_info.tcp_flow_nb][tcp_info.tcp_cc] = []
        gp = None
        if tcp_info.tcp_direction == FlowType.UPLOAD:
            gp = tcp_info.tcp_goodput_pcap
        elif tcp_info.tcp_direction == FlowType.DOWNLOAD:
            gp = tcp_info.tcp_goodput_app
        else:
            raise Exception("Unsupported tcp flow type: {}".format(tcp_info.tcp_direction))
        cdf_dict[tcp_info.tcp_direction][tcp_info.tcp_flow_nb][tcp_info.tcp_cc].append(gp)

    for direction, v1 in cdf_dict.items():
        for flow_nb, v2 in v1.items():
            for cc, v3 in v2.items():
                #number of instances, cdf
                cdf_dict[direction][flow_nb][cc] = (len(v3), __get_cdf(v3))
    return cdf_dict

def plot_tcp_avg_goodput_cdf(session_dict, output_dir):
    set_matplotlib_env()
    for db_name, session in session_dict.items():
        with open(os.path.join(output_dir, db_name+"_tcp_tester_grouping_info.csv"), "w") as f:
            csv_f = csv.writer(f)
            cdf_dict = get_tcp_avg_goodput_cdf(session)
            capitalize_func = lambda x:x if str.isupper(x[0]) else str.upper(x[0])+x[1:]
            for direction, v1 in cdf_dict.items():
                comp_flow = {}
                fig, sp = plt.subplots(len(v1), 1, sharex=True, figsize=(10, 15), gridspec_kw={"wspace":0.05, "hspace":0.40})
                sp_id = 0
                csv_f.writerow(["fig1 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"])
                csv_f.writerow(["grouped by concurrency"])
                for flow_nb, v2 in sorted(v1.items()):
                    sp[sp_id].set_prop_cycle(PLOT_CYCLER)
                    for cc, v3 in sorted(v2.items()):
                        group_size = v3[0]
                        x, y, mean, std, mmax, mmin = v3[1]

                        quantiles = [__get_quantile_from_cdf(x, y, 0.25), __get_quantile_from_cdf(x, y, 0.5), __get_quantile_from_cdf(x, y, 0.75), __get_quantile_from_cdf(x, y, 0.9), mean, std, mmax, mmin]
                        csv_f.writerow([direction.value, flow_nb, cc, group_size, "|"] + quantiles)
                        sp[sp_id].plot(x, y, drawstyle="default", label="{}".format(cc.upper()))

                        #x, y = __cdf_to_ccdf(x, y)
                        #quantiles = [__get_quantile_from_ccdf(x, y, 0.25), __get_quantile_from_ccdf(x, y, 0.5), __get_quantile_from_ccdf(x, y, 0.75), __get_quantile_from_ccdf(x, y, 0.9)]
                        #csv_f.writerow([direction.value, flow_nb, cc, group_size, "|"] + quantiles)
                        #sp[sp_id].step(x, y, where="pre", label="{}".format(cc.upper()))

                        #prepare for comparison plot between concurrent flows
                        if cc not in comp_flow:
                            comp_flow[cc] = {}
                        comp_flow[cc][flow_nb] = v3
                    sp[sp_id].set_ylim(0, 1)
                    sp[sp_id].set_title("# of flows: {}".format(flow_nb))
                    #sp[sp_id].set_yticks(list(map(lambda x:x/10, range(0, 11, 2))))
                    sp[sp_id].grid()
                    sp[sp_id].set_ylabel("CDF")
                    sp[sp_id].xaxis.set_tick_params(which="both", labelbottom=True)
                    sp[sp_id].xaxis.set_minor_locator(AutoMinorLocator())
                    sp[sp_id].yaxis.set_minor_locator(AutoMinorLocator())
                    sp[sp_id].legend(ncol=1, loc="lower right")
                    #sp[sp_id].legend(ncol=1, loc="upper right")

                    sp_id += 1

                sp[-1].set_xlabel("Average {} goodput (Mbit/s)".format((direction.value)))
                #fig.suptitle("Average {} Throughput CDF".format(direction.value))
                fig.savefig(os.path.join(output_dir, db_name+"_tcp_avg_goodput_cdf_{}_flownb_fixed".format(direction.value)+FIG_EXT), format=FIG_FMT, bbox_inches="tight")

                csv_f.writerow(["fig2>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"])
                csv_f.writerow(["grouped by CC"])
                fig, sp = plt.subplots(len(comp_flow), 1, sharex=True, figsize=(10, 7), gridspec_kw={"wspace":0.05, "hspace":0.30})
                sp_id = 0
                for cc, v2 in sorted(comp_flow.items()):
                    sp[sp_id].set_prop_cycle(PLOT_CYCLER)
                    for flow_nb, v3 in sorted(v2.items()):
                        group_size = v3[0]
                        x, y, mean, std, mmax, mmin = v3[1]

                        quantiles = [__get_quantile_from_cdf(x, y, 0.25), __get_quantile_from_cdf(x, y, 0.5), __get_quantile_from_cdf(x, y, 0.75), __get_quantile_from_cdf(x, y, 0.9), mean, std, mmax, mmin]
                        csv_f.writerow([direction.value, cc, flow_nb, group_size, "|"] + quantiles)
                        sp[sp_id].plot(x, y, drawstyle="default", label="{}".format(flow_nb))

                        #x, y = __cdf_to_ccdf(x, y)
                        #quantiles = [__get_quantile_from_ccdf(x, y, 0.25), __get_quantile_from_ccdf(x, y, 0.5), __get_quantile_from_ccdf(x, y, 0.75), __get_quantile_from_ccdf(x, y, 0.9)]
                        #csv_f.writerow([direction.value, cc, flow_nb, group_size, "|"] + quantiles)
                        #sp[sp_id].step(x, y, where="pre", label="{}".format(flow_nb))

                    sp[sp_id].set_ylim(0, 1)
                    sp[sp_id].set_title("{}".format(str.upper(cc)))
                    #sp[sp_id].set_yticks(list(map(lambda x:x/10, range(0, 11))))
                    sp[sp_id].grid()
                    sp[sp_id].set_ylabel("CDF")
                    sp[sp_id].xaxis.set_tick_params(which="both", labelbottom=True)
                    sp[sp_id].xaxis.set_minor_locator(AutoMinorLocator())
                    sp[sp_id].yaxis.set_minor_locator(AutoMinorLocator())
                    sp[sp_id].legend(ncol=1, title="# of flows", loc="lower right")
                    #sp[sp_id].legend(ncol=3, title="# of flows", loc="upper right")
                    sp_id += 1

                sp[-1].set_xlabel("Average {} goodput (Mbit/s)".format((direction.value)))
                #fig.suptitle("Average {} Throughput CDF".format(direction.value))
                fig.savefig(os.path.join(output_dir, db_name+"_tcp_avg_goodput_cdf_{}_cc_fixed".format(direction.value)+FIG_EXT), format=FIG_FMT, bbox_inches="tight")

def plot_tcp_avg_goodput_ccdf(session_dict, output_dir):
    set_matplotlib_env()
    for db_name, session in session_dict.items():
        with open(os.path.join(output_dir, db_name+"_tcp_tester_grouping_info_ccdf.csv"), "w") as f:
            csv_f = csv.writer(f)
            cdf_dict = get_tcp_avg_goodput_cdf(session)
            capitalize_func = lambda x:x if str.isupper(x[0]) else str.upper(x[0])+x[1:]
            for direction, v1 in cdf_dict.items():
                comp_flow = {}
                fig, sp = plt.subplots(len(v1), 1, sharex=True, figsize=(10, 15), gridspec_kw={"wspace":0.05, "hspace":0.40})
                sp_id = 0
                csv_f.writerow(["fig1 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"])
                csv_f.writerow(["grouped by concurrency"])
                for flow_nb, v2 in sorted(v1.items()):
                    sp[sp_id].set_prop_cycle(PLOT_CYCLER)
                    for cc, v3 in sorted(v2.items()):
                        group_size = v3[0]
                        x, y, mean, std, mmax, mmin = v3[1]
                        quantiles = [__get_quantile_from_cdf(x, y, 0.25), __get_quantile_from_cdf(x, y, 0.5), __get_quantile_from_cdf(x, y, 0.75), __get_quantile_from_cdf(x, y, 0.9), mean, std, mmax, mmin]
                        x, y = __cdf_to_ccdf(x, y)
                        csv_f.writerow([direction.value, flow_nb, cc, group_size, "|"] + quantiles)
                        sp[sp_id].plot(x, y, drawstyle="default", label="{}".format(cc.upper()))

                        #prepare for comparison plot between concurrent flows
                        if cc not in comp_flow:
                            comp_flow[cc] = {}
                        comp_flow[cc][flow_nb] = v3

                    sp[sp_id].set_ylim(0, 1)
                    sp[sp_id].set_title("# of flows: {}".format(flow_nb))
                    #sp[sp_id].set_yticks(list(map(lambda x:x/10, range(0, 11, 2))))
                    sp[sp_id].grid()
                    sp[sp_id].set_ylabel("CCDF")
                    sp[sp_id].xaxis.set_tick_params(which="both", labelbottom=True)
                    sp[sp_id].xaxis.set_minor_locator(AutoMinorLocator())
                    sp[sp_id].yaxis.set_minor_locator(AutoMinorLocator())
                    sp[sp_id].legend(ncol=1, loc="upper right")

                    sp_id += 1

                sp[-1].set_xlabel("Average {} goodput (Mbit/s)".format((direction.value)))
                fig.savefig(os.path.join(output_dir, db_name+"_tcp_avg_goodput_{}_flownb_fixed_ccdf".format(direction.value)+FIG_EXT), format=FIG_FMT, bbox_inches="tight")

                csv_f.writerow(["fig2>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"])
                csv_f.writerow(["grouped by CC"])
                fig, sp = plt.subplots(len(comp_flow), 1, sharex=True, figsize=(10, 7), gridspec_kw={"wspace":0.05, "hspace":0.30})
                sp_id = 0
                for cc, v2 in sorted(comp_flow.items()):
                    sp[sp_id].set_prop_cycle(PLOT_CYCLER)
                    for flow_nb, v3 in sorted(v2.items()):
                        group_size = v3[0]
                        x, y, mean, std, mmax, mmin = v3[1]
                        quantiles = [__get_quantile_from_cdf(x, y, 0.25), __get_quantile_from_cdf(x, y, 0.5), __get_quantile_from_cdf(x, y, 0.75), __get_quantile_from_cdf(x, y, 0.9), mean, std, mmax, mmin]
                        x, y = __cdf_to_ccdf(x, y)
                        csv_f.writerow([direction.value, cc, flow_nb, group_size, "|"] + quantiles)
                        sp[sp_id].plot(x, y, drawstyle="default", label="{}".format(flow_nb))

                    sp[sp_id].set_ylim(0, 1)
                    sp[sp_id].set_title("{}".format(str.upper(cc)))
                    #sp[sp_id].set_yticks(list(map(lambda x:x/10, range(0, 11))))
                    sp[sp_id].grid()
                    sp[sp_id].set_ylabel("CCDF")
                    sp[sp_id].xaxis.set_tick_params(which="both", labelbottom=True)
                    sp[sp_id].xaxis.set_minor_locator(AutoMinorLocator())
                    sp[sp_id].yaxis.set_minor_locator(AutoMinorLocator())
                    sp[sp_id].legend(ncol=1, title="# of flows", loc="upper right")
                    sp_id += 1

                sp[-1].set_xlabel("Average {} goodput (Mbit/s)".format((direction.value)))
                fig.savefig(os.path.join(output_dir, db_name+"_tcp_avg_goodput_{}_cc_fixed_ccdf".format(direction.value)+FIG_EXT), format=FIG_FMT, bbox_inches="tight")

#customized plotting func for IMC paper
def plot_tight_tcp_avg_goodput_cdf(session_dict, output_dir):
    set_matplotlib_env()
    for db_name, session in session_dict.items():
        with open(os.path.join(output_dir, db_name+"_tcp_tester_grouping_info_tight.csv"), "w") as f:
            csv_f = csv.writer(f)
            cdf_dict = get_tcp_avg_goodput_cdf(session)
            capitalize_func = lambda x:x if str.isupper(x[0]) else str.upper(x[0])+x[1:]
            for direction, v1 in cdf_dict.items():
                comp_flow = {}
                for flow_nb, v2 in sorted(v1.items()):
                    for cc, v3 in sorted(v2.items()):
                        #prepare for comparison plot between concurrent flows
                        if cc not in comp_flow:
                            comp_flow[cc] = {}
                        comp_flow[cc][flow_nb] = v3
                csv_f.writerow(["fig2>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"])
                csv_f.writerow(["grouped by CC"])
                fig, sp = plt.subplots(1, 1, sharex=True)
                sp.set_prop_cycle(PLOT_CYCLER)
                for cc, v2 in sorted(comp_flow.items()):
                    for flow_nb, v3 in sorted(v2.items()):
                        if flow_nb == 4 or flow_nb == 16:
                            group_size = v3[0]
                            x, y = v3[1]
                            csv_f.writerow([direction.value, cc, flow_nb, group_size])
                            sp.plot(x, y, drawstyle="default", label="{}-{}".format(cc, flow_nb))
                sp.set_ylim(0, 1)
                sp.set_ylabel("Frac. of associations")
                #sp.set_yticks(list(map(lambda x:x/10, range(0, 11))))
                sp.grid()
                sp.xaxis.set_tick_params(which="both")
                sp.xaxis.set_minor_locator(AutoMinorLocator())
                sp.yaxis.set_minor_locator(AutoMinorLocator())
                sp.legend(ncol=1, loc="lower right")
                sp.set_xlabel("Average {} goodput (Mbit/s)".format((direction.value)))
                fig.savefig(os.path.join(output_dir, db_name+"_tcp_avg_goodput_cdf_{}_cc_fixed_tight".format(direction.value)+FIG_EXT), format=FIG_FMT, bbox_inches="tight")


#TCP average goodput CDF
    # don't distinguish flow number
    # classify cdf by CC, upload/download
def get_tcp_avg_goodput_nofn_cdf(session):
    tcp_infos = session.query(APTCPInfo.tcp_direction, APTCPInfo.tcp_cc, APTCPInfo.tcp_goodput_app, APTCPInfo.tcp_goodput_pcap).filter(APTCPInfo.tcp_t_s != None).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    cdf_dict = {}
    for tcp_info in tcp_infos:
        if tcp_info.tcp_direction not in cdf_dict:
            cdf_dict[tcp_info.tcp_direction] = {}
        if tcp_info.tcp_cc not in cdf_dict[tcp_info.tcp_direction]:
            cdf_dict[tcp_info.tcp_direction][tcp_info.tcp_cc] = []
        gp = None
        if tcp_info.tcp_direction == FlowType.UPLOAD:
            gp = tcp_info.tcp_goodput_pcap
        elif tcp_info.tcp_direction == FlowType.DOWNLOAD:
            gp = tcp_info.tcp_goodput_app
        else:
            raise Exception("Unsupported tcp flow type: {}".format(tcp_info.tcp_direction))
        cdf_dict[tcp_info.tcp_direction][tcp_info.tcp_cc].append(gp)

    for direction, v1 in cdf_dict.items():
        for cc, v3 in v1.items():
            #number of instances, cdf
            cdf_dict[direction][cc] = (len(v3), __get_cdf(v3))
    return cdf_dict


def plot_tcp_avg_goodput_nofn_cdf(session_dict, output_dir):
    set_matplotlib_env()
    for db_name, session in session_dict.items():
        with open(os.path.join(output_dir, db_name+"_tcp_tester_grouping_info_nofn.csv"), "w") as f:
            csv_f = csv.writer(f)
            cdf_dict = get_tcp_avg_goodput_nofn_cdf(session)
            capitalize_func = lambda x:x if str.isupper(x[0]) else str.upper(x[0])+x[1:]
            for direction, v1 in cdf_dict.items():
                fig, sp = plt.subplots(1, 1, sharex=True)
                sp.set_prop_cycle(PLOT_CYCLER)
                csv_f.writerow(["fig2>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"])
                csv_f.writerow(["grouped by CC"])
                for cc, v2 in sorted(v1.items()):
                    group_size = v2[0]
                    x, y, mean, std, mmax, mmin = v2[1]
                    csv_f.writerow([direction.value, cc, group_size])

                    quantiles = [__get_quantile_from_cdf(x, y, 0.25), __get_quantile_from_cdf(x, y, 0.5), __get_quantile_from_cdf(x, y, 0.75), __get_quantile_from_cdf(x, y, 0.9), mean, std, mmax, mmin]
                    csv_f.writerow([0.25, 0.5, 0.75, 0.9, "mean", "std"])
                    csv_f.writerow(quantiles)
                    sp.plot(x, y, drawstyle="default", label="{}".format(cc.upper()))

                    #x, y = __cdf_to_ccdf(x, y)
                    #quantiles = [__get_quantile_from_ccdf(x, y, 0.25), __get_quantile_from_ccdf(x, y, 0.5), __get_quantile_from_ccdf(x, y, 0.75), __get_quantile_from_ccdf(x, y, 0.9)]
                    #csv_f.writerow([0.25, 0.5, 0.75, 0.9])
                    #csv_f.writerow(quantiles)
                    #sp.step(x, y, where="pre", label="{}".format(cc))
                sp.set_ylim(0, 1)
                sp.set_ylabel("Frac. of associations")
                #sp.set_ylabel("Complementary CDF")
                #sp.set_yticks(list(map(lambda x:x/10, range(0, 11))))
                sp.grid()
                sp.xaxis.set_tick_params(which="both")
                sp.xaxis.set_minor_locator(AutoMinorLocator())
                sp.yaxis.set_minor_locator(AutoMinorLocator())
                sp.legend(ncol=1, loc="lower right")
                #sp.legend(ncol=2, loc="upper right")
                sp.set_xlabel("Average {} goodput (Mbit/s)".format((direction.value)))
                fig.savefig(os.path.join(output_dir, db_name+"_tcp_avg_goodput_cdf_{}_cc_fixed_nofn".format(direction.value)+FIG_EXT), format=FIG_FMT, box_inches="tight")

def plot_tcp_avg_goodput_nofn_ccdf(session_dict, output_dir):
    set_matplotlib_env()
    for db_name, session in session_dict.items():
        with open(os.path.join(output_dir, db_name+"_tcp_tester_grouping_info_nofn_ccdf.csv"), "w") as f:
            csv_f = csv.writer(f)
            cdf_dict = get_tcp_avg_goodput_nofn_cdf(session)
            capitalize_func = lambda x:x if str.isupper(x[0]) else str.upper(x[0])+x[1:]
            for direction, v1 in cdf_dict.items():
                fig, sp = plt.subplots(1, 1, sharex=True)
                sp.set_prop_cycle(PLOT_CYCLER)
                csv_f.writerow(["fig2>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"])
                csv_f.writerow(["grouped by CC"])
                for cc, v2 in sorted(v1.items()):
                    group_size = v2[0]
                    x, y, mean, std, mmax, mmin = v2[1]
                    csv_f.writerow([direction.value, cc, group_size])

                    quantiles = [__get_quantile_from_cdf(x, y, 0.25), __get_quantile_from_cdf(x, y, 0.5), __get_quantile_from_cdf(x, y, 0.75), __get_quantile_from_cdf(x, y, 0.9), mean, std, mmax, mmin]
                    x, y = __cdf_to_ccdf(x, y)
                    csv_f.writerow([0.25, 0.5, 0.75, 0.9, "mean", "std"])
                    csv_f.writerow(quantiles)
                    sp.plot(x, y, drawstyle="default", label="{}".format(cc.upper()))

                sp.set_ylim(0, 1)
                sp.set_ylabel("Frac. of associations")
                #sp.set_yticks(list(map(lambda x:x/10, range(0, 11))))
                sp.grid()
                sp.xaxis.set_minor_locator(AutoMinorLocator())
                sp.yaxis.set_minor_locator(AutoMinorLocator())
                sp.legend(ncol=1, loc="upper right")
                sp.set_xlabel("Average {} goodput (Mbit/s)".format((direction.value)))
                fig.savefig(os.path.join(output_dir, db_name+"_tcp_avg_goodput_{}_cc_fixed_nofn_ccdf".format(direction.value)+FIG_EXT), format=FIG_FMT, bbox_inches="tight")

def get_download_volume_per_ap_cdf(session):
    data_infos = session.query(APTCPInfo.tcp_total_bytes_app).filter(APTCPInfo.tcp_t_s != None, APTCPInfo.tcp_direction == FlowType.DOWNLOAD).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    data_vols = []
    for info in data_infos:
        data_vol = info.tcp_total_bytes_app
        #data in MB unit
        data_vols.append(data_vol / 1024.0 / 1024.0)
    return __get_cdf(data_vols)

@cdf_plotter("download_volume_cdf"+FIG_EXT, "Download data volume (MB)", log=True, ymin=0, ymax=0.9)
def plot_download_volume_per_ap_cdf(session):
    return get_download_volume_per_ap_cdf(session)


@ccdf_plotter("download_volume_ccdf"+FIG_EXT, "Download data volume (MB)", log=True, ymin=0.1, ymax=1, legend_loc="lower left")
def plot_download_volume_per_ap_ccdf(session):
    return get_download_volume_per_ap_cdf(session)

def get_upload_volume_per_ap_cdf(session):
    data_infos = session.query(APTCPInfo.tcp_total_bytes_pcap).filter(APTCPInfo.tcp_t_s != None, APTCPInfo.tcp_direction == FlowType.UPLOAD).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    data_vols = []
    for info in data_infos:
        data_vol = info.tcp_total_bytes_pcap
        #data in MB unit
        data_vols.append(data_vol / 1024.0 / 1024.0)
    return __get_cdf(data_vols)

@cdf_plotter("upload_volume_cdf"+FIG_EXT, "Upload data volume (MB)", log=True, ymin=0, ymax=0.9)
def plot_upload_volume_per_ap_cdf(session):
    return get_upload_volume_per_ap_cdf(session)


@ccdf_plotter("upload_volume_ccdf"+FIG_EXT, "Upload data volume (MB)", log=True, ymin=0.1, ymax=1, legend_loc="lower left")
def plot_upload_volume_per_ap_ccdf(session):
    return get_upload_volume_per_ap_cdf(session)


def plot_ip_changing(session_dict, output_dir):
    set_matplotlib_env()
    for db_name, session in session_dict.items():
        #only plot <= 10days traces
        date_list = session.query(Experiment.start_time).all()
        date_list = set(datetime.utcfromtimestamp(x.start_time).date() for x in date_list)
        date_list = sorted(date_list)
        date = date_list[10] if len(date_list) > 10 else None
        exps = None
        if date:
            target_ts = datetime(year=date.year, month=date.month, day=date.day, hour=0, minute=0, second=0).timestamp()
            exps = session.query(Experiment).filter(Experiment.start_time < target_ts).order_by(Experiment.start_time).all()
        else:
            exps = session.query(Experiment).order_by(Experiment.start_time).all()
        trips = []
        for exp in exps:
            if len(trips) !=0 and (exp.start_time - trips[-1][1]) <= 300:
                #the gap between two consecutive data collections should not exceed 30s
                trips[-1][1] = exp.end_time
            else:
                trips.append([exp.start_time, exp.end_time])

        ip_dict = {None:[0, 0]}
        #ip index array of APs
        aps = []
        #borders between two experiments
        #borders between days
        borders = []
        #last_date = None
        #curr_date = None
        #local_tz = timezone(timedelta(hours=DB_TIMEZONE[db_name]))
        ip_change_count = 0
        arr_ip_ch = 0
        arr_ip_ch_count = []
        total_ip_count = 0
        for trip in trips:
            ap_ips = session.query(APTCPInfo.l3_ip).filter(APTCPInfo.l2_conn_t_s >= trip[0], APTCPInfo.l2_conn_t_s <= trip[1]).order_by(APTCPInfo.l3_dhcp_t_s).all()
            #if len(ap_ips):
                #curr_date = datetime.utcfromtimestamp(exp.start_time).replace(tzinfo=timezone.utc)
                #curr_date = curr_date.astimezone(local_tz)
                #if last_date == None or curr_date.day != last_date.day:
                #    borders.append((curr_date.strftime("%Y/%m/%d"), len(aps)))
                #last_date = curr_date
            last_ip = None
            for ip in ap_ips:
                if ip[0] != None:
                    if last_ip == None:
                        last_ip = ip[0]
                    if last_ip != ip[0]:
                        ip_change_count += 1
                        arr_ip_ch += 1
                    total_ip_count += 1
                if ip.l3_ip not in ip_dict:
                    ip_dict[ip.l3_ip] = [len(ip_dict), 0]
                #counter += 1
                ip_dict[ip.l3_ip][1] += 1
                #record ip index
                aps.append(ip_dict[ip.l3_ip][0])
            if len(ap_ips) and arr_ip_ch:
                arr_ip_ch_count.append(len(ap_ips)/arr_ip_ch)
            arr_ip_ch = 0
            borders.append((datetime.utcfromtimestamp(trip[1]).strftime("%Y/%m/%d/%H%M"), len(aps)))

        print("{} ip_change: {}, total_ip: {}, avg change per drive {}".format(db_name, ip_change_count, total_ip_count, np.mean(arr_ip_ch_count) if len(arr_ip_ch_count) else None))

        ymin = 0
        ymax = len(ip_dict)
        #sorted by ip index
        plt.plot(aps, "x", c='r', markersize=3, clip_on=False)
        plt.tick_params(axis="x", which="both", length=0)
        plt.tick_params(axis="y", which="both", length=0)
        plt.xlabel("Association ID")
        plt.ylabel("IP address ID")
        plt.ylim(ymin, ymax)
        plt.xlim(0, len(aps))


        #y_tick_labels = (x[0] for x in sorted(ip_dict.items(), key=lambda x:x[1]))
        #locs = list(range(0, ymax))
        #label_size = 20 if 20 < ymax else ymax
        #label_gap = ymax // label_size
        #labels = [""] * ymax
        #for loc in range(0, ymax, label_gap):
        #    labels[loc] = loc
        #plt.yticks(locs, labels)
        for day, bd_x in borders:
            #bd_x -= 0.5
            plt.axvline(bd_x, color='grey', linestyle='dashed')#, linewidth=0.5)
        ax = plt.gca()
        #ax.spines['top'].set_visible(False)
        #ax.spines['right'].set_visible(False)
        plt.savefig(os.path.join(output_dir, db_name+"_ip_changing"+FIG_EXT), format=FIG_FMT, bbox_inches="tight")
        plt.close()

def get_dhcp_info_per_db(session):
    distinct_essid = session.query(distinct(APTCPInfo.l2_essid)).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    dhcp_server_dict = {}
    for ssid in distinct_essid:
        dhcp_servers = session.query(APTCPInfo.l3_dhcp_server, func.count(APTCPInfo.l3_dhcp_server), func.count(distinct(APTCPInfo.l3_ip))).filter(APTCPInfo.l2_essid == ssid[0]).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.l3_dhcp_server != None).group_by(APTCPInfo.l3_dhcp_server).all()
        dhcp_server_dict[ssid[0]] = dhcp_servers
    return dhcp_server_dict
            

def output_dhcp_server_info(session_dict, output_dir):
    for db_name, session in session_dict.items():
        dhcp_server_dict = get_dhcp_info_per_db(session)
        with open(os.path.join(output_dir, db_name+"_dhcp_server_info.csv"), "w") as f:
            csv_f = csv.writer(f)
            for ssid, dhcp_servers in dhcp_server_dict.items():
                csv_f.writerow(["SSID", ssid])
                csv_f.writerow(["DHCP server IP", "# of distinct client IP", "# of client IP"])
                for dhcp_server in dhcp_servers:
                    csv_f.writerow([dhcp_server[0], dhcp_server[2], dhcp_server[1]])


def plot_ip_changing_by_ssid(session_dict, output_dir, ssid_dict):
    set_matplotlib_env()
    for db_name, ssid_list in ssid_dict.items():
        session = session_dict[db_name]
        #only plot <= 10days traces
        date_list = session.query(Experiment.start_time).all()
        date_list = set(datetime.utcfromtimestamp(x.start_time).date() for x in date_list)
        date_list = sorted(date_list)
        date = date_list[5] if len(date_list) > 5 else None
        exps = None
        if date:
            target_ts = datetime(year=date.year, month=date.month, day=date.day, hour=0, minute=0, second=0).timestamp()
            exps = session.query(Experiment).filter(Experiment.start_time < target_ts).order_by(Experiment.start_time).all()
        else:
            exps = session.query(Experiment).order_by(Experiment.start_time).all()
        trips = []
        for exp in exps:
            if len(trips) !=0 and (exp.start_time - trips[-1][1]) <= 180:
                #the gap between two consecutive data collections should not exceed 30s
                trips[-1][1] = exp.end_time
            else:
                trips.append([exp.start_time, exp.end_time])

        for ssid in ssid_list:
            ip_dict = {None:[0, 0]}
            aps = []
            borders = []
            ip_change_count = 0
            arr_ip_ch = 0
            arr_ip_ch_count = []
            total_ip_count = 0
            for trip in trips:
                ap_ips = session.query(APTCPInfo.l3_ip).filter(APTCPInfo.l2_essid.like(ssid)).filter(APTCPInfo.l2_conn_t_s >= trip[0], APTCPInfo.l2_conn_t_s <= trip[1]).order_by(APTCPInfo.l3_dhcp_t_s).all()
                #if len(ap_ips):
                    #curr_date = datetime.utcfromtimestamp(exp.start_time).replace(tzinfo=timezone.utc)
                    #curr_date = curr_date.astimezone(local_tz)
                    #if last_date == None or curr_date.day != last_date.day:
                    #    borders.append((curr_date.strftime("%Y/%m/%d"), len(aps)))
                    #last_date = curr_date
                last_ip = None
                for ip in ap_ips:
                    if ip[0] != None:
                        if last_ip == None:
                            last_ip = ip[0]
                        if last_ip != ip[0]:
                            ip_change_count += 1
                            arr_ip_ch += 1
                        total_ip_count += 1
                    if ip.l3_ip not in ip_dict:
                        ip_dict[ip.l3_ip] = [len(ip_dict), 0]
                    #counter += 1
                    ip_dict[ip.l3_ip][1] += 1
                    #record ip index
                    aps.append(ip_dict[ip.l3_ip][0])
                if len(ap_ips) and arr_ip_ch:
                    arr_ip_ch_count.append(len(ap_ips)/arr_ip_ch)
                arr_ip_ch = 0
                borders.append((datetime.utcfromtimestamp(trip[1]).strftime("%Y/%m/%d/%H%M"), len(aps)))

            print("{} {} ip_change: {}, total_ip: {}, avg change per drive {}".format(db_name, ssid, ip_change_count, total_ip_count, np.mean(arr_ip_ch_count) if len(arr_ip_ch_count) else None))

            ymin = 0
            ymax = len(ip_dict)
            #sorted by ip index
            plt.plot(aps, "x", c='r', markersize=3, clip_on=False)
            plt.tick_params(axis="x", which="both", length=0)
            plt.tick_params(axis="y", which="both", length=0)
            plt.xlabel("Association ID")
            plt.ylabel("IP address ID")
            plt.ylim(ymin, ymax)
            plt.xlim(0, len(aps))


            #y_tick_labels = (x[0] for x in sorted(ip_dict.items(), key=lambda x:x[1]))
            #locs = list(range(0, ymax))
            #label_size = 20 if 20 < ymax else ymax
            #label_gap = ymax // label_size
            #labels = [""] * ymax
            #for loc in range(0, ymax, label_gap):
            #    labels[loc] = loc
            #plt.yticks(locs, labels)
            for day, bd_x in borders:
                #bd_x -= 0.5
                plt.axvline(bd_x, color='grey', linestyle='dashed')#, linewidth=0.5)
            ax = plt.gca()
            #ax.spines['top'].set_visible(False)
            #ax.spines['right'].set_visible(False)
            plt.savefig(os.path.join(output_dir, db_name+"_"+ssid+"_ip_changing"+FIG_EXT), format=FIG_FMT, bbox_inches="tight")
            plt.close()

def get_freq_change_per_ap(session):
    res = session.query(APTCPInfo.l2_bssid, func.count(distinct(APTCPInfo.l2_freq))).filter(APTCPInfo.l2_freq != None).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).group_by(APTCPInfo.l2_bssid).all()
    no_change = list(filter(lambda x:x[1]<=1, res))
    changed = list(filter(lambda x:x[1]>1, res))
    freq_duration_list = []
    for ap in changed:
        ap_freqs = session.query(APTCPInfo.l2_auth_t_s, APTCPInfo.l2_conn_t_e, APTCPInfo.l2_freq).filter(APTCPInfo.l2_freq != None).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).order_by(APTCPInfo.l2_auth_t_s).all()
        temp = []
        curr_freq_t_s = None
        curr_freq_t_e = None
        last_freq = None
        total_changed = 0
        for freq in ap_freqs:
            if last_freq == None:
                last_freq = freq[2]
                curr_freq_t_s = freq[0]
                curr_freq_t_e = freq[1]
            else:
                if last_freq == freq[2]:
                    curr_freq_t_e = freq[1]
                else:
                    temp.append(curr_freq_t_e - curr_freq_t_s)
                    total_changed += 1
                    curr_freq_t_s = freq[0]
                    curr_freq_t_e = freq[1]
                    last_freq = freq[2]
        temp.append(curr_freq_t_e-curr_freq_t_s)
        freq_duration_list += temp

    mean_freq_dura = None
    std_freq_dura = None
    if len(freq_duration_list) != 0:
        mean_freq_dura = np.mean(freq_duration_list)
        std_freq_dura = np.std(freq_duration_list)
    return len(res), len(no_change), len(changed), mean_freq_dura, std_freq_dura

def output_freq_change_per_ap(session_dict, output_dir):
    for db_name, session in sorted(session_dict.items()):
        unique_ap_num, no_changed_ap_num, changed, mean_freq_dura, std_freq_dura = get_freq_change_per_ap(session)
        output_path = os.path.join(output_dir, db_name+"_ap_freq_change.csv")
        with open(output_path, "w") as f:
            csv_f = csv.writer(f)
            csv_f.writerow([db_name, "total ap", "no change", "changed"])
            csv_f.writerow(["", unique_ap_num, no_changed_ap_num, changed])
            csv_f.writerow(["", "mean freq duration", "std freq duration"])
            csv_f.writerow(["", mean_freq_dura, std_freq_dura])


def generate_ip_changing_data(session_dict, output_dir, ssid_dict):
    for db_name, ssid_list in ssid_dict.items():
        session = session_dict[db_name]
        #only plot <= 5days traces
        date_list = session.query(Experiment.start_time).all()
        date_list = set(datetime.utcfromtimestamp(x.start_time).date() for x in date_list)
        date_list = sorted(date_list)
        #date = date_list[5] if len(date_list) > 5 else None
        date = None
        exps = None
        if date:
            target_ts = datetime(year=date.year, month=date.month, day=date.day, hour=0, minute=0, second=0).timestamp()
            exps = session.query(Experiment).filter(Experiment.start_time < target_ts).order_by(Experiment.start_time).all()
        else:
            exps = session.query(Experiment).order_by(Experiment.start_time).all()
        trips = []
        for exp in exps:
            if len(trips) !=0 and (exp.start_time - trips[-1][1]) <= 180:
                #the gap between two consecutive data collections should not exceed 30s
                trips[-1][1] = exp.end_time
            else:
                trips.append([exp.start_time, exp.end_time])
        # ssid : (trip_t_s, trip_t_e, [(ip, ip_t_s, ip_t_e), ...])
        ip_changing_data = {}
        for ssid in ssid_list:
            ip_dict = {None:[0, 0]}
            aps = []
            ip_change_count = 0
            arr_ip_ch = 0
            arr_ip_ch_count = []
            total_ip_count = 0
            ip_changing_data[ssid] = []
            for trip in trips:
                ap_ips = session.query(APTCPInfo.l3_ip, APTCPInfo.l3_ip_t_s, APTCPInfo.l3_ip_t_e).filter(APTCPInfo.l2_essid.like(ssid)).filter(APTCPInfo.l3_ip != None).filter(APTCPInfo.l2_conn_t_s >= trip[0], APTCPInfo.l2_conn_t_s <= trip[1]).order_by(APTCPInfo.l3_ip_t_s).all()
                if ap_ips != None:
                    ap_ips = [(x[0], float(x[1]), float(x[2])) for x in ap_ips]
                else:
                    ap_ips = []
                ip_changing_data[ssid].append((float(trip[0]), float(trip[1]), ap_ips))
        output_path = os.path.join(output_dir, db_name+"_ip_change.json")
        with open(output_path, "w") as f:
            json.dump(ip_changing_data, f)
        del ip_changing_data

def _create_gps_trace():
    gps_trace = gpxpy.gpx.GPX()
    gps_trace.tracks.append(gpxpy.gpx.GPXTrack())
    return gps_trace

def _add_segments(gps_trace, gps_data_points):
    track = gps_trace.tracks[0]
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)
    for p in gps_data_points:
        segment.points.append(gpxpy.gpx.GPXTrackPoint(p.latitude, p.longitude, p.elevation, datetime.utcfromtimestamp(p.time)))

#THis function is only used for diagnosis about the reason of outliers
def _diagnose_gps_trace(session):
    l2_conn_trace = _create_gps_trace()
    l2_gps = session.query(GPS).filter(GPS.time >= 1530813644, GPS.time <= 1530814533).order_by(GPS.time).all()
    _add_segments(l2_conn_trace, l2_gps)
    return l2_conn_trace

#THis function is only used for diagnosis about the reason of outliers
def diagnose_gps_trace(session, output_dir):
    l2_conn_trace = _diagnose_gps_trace(session)
    with open(os.path.join(output_dir, "diagnosis.gpx"), "w") as f:
        f.write(l2_conn_trace.to_xml())

def get_drive_trace(session):
    exps = session.query(Experiment).order_by(Experiment.start_time).all()
    exp_trace = _create_gps_trace()
    for exp in exps:
        exp_gps = session.query(GPS).filter(GPS.time >= exp.start_time, GPS.time <= exp.end_time).order_by(GPS.time).all()
        _add_segments(exp_trace, exp_gps)
    return (exp_trace, )

def get_gps_traces(session):
    exps = session.query(Experiment).order_by(Experiment.start_time).all()
    exp_trace = _create_gps_trace()
    l2_conn_trace = _create_gps_trace()
    l3_conn_trace = _create_gps_trace()
    tcp_conn_trace = _create_gps_trace()
    for exp in exps:
        exp_gps = session.query(GPS).filter(GPS.time >= exp.start_time, GPS.time <= exp.end_time).order_by(GPS.time).all()
        _add_segments(exp_trace, exp_gps)
        del exp_gps

        l2_conns = session.query(APTCPInfo.l2_conn_t_s, APTCPInfo.l2_conn_t_e).filter(APTCPInfo.l2_conn_t_s >= exp.start_time, APTCPInfo.l2_conn_t_e <= exp.end_time).order_by(APTCPInfo.l2_conn_t_s).all()

        for l2_conn in l2_conns:
            l2_gps = session.query(GPS).filter(GPS.time >= l2_conn.l2_conn_t_s, GPS.time <= l2_conn.l2_conn_t_e).order_by(GPS.time).all()
            _add_segments(l2_conn_trace, l2_gps)
        del l2_conns

        l3_conns = session.query(APTCPInfo.l3_ip_t_s, APTCPInfo.l3_ip_t_e).filter(APTCPInfo.l3_ip != None).filter(APTCPInfo.l3_ip_t_s >= exp.start_time, APTCPInfo.l3_ip_t_e <= exp.end_time).order_by(APTCPInfo.l3_ip_t_s).all()

        for l3_conn in l3_conns:
            l3_gps = session.query(GPS).filter(GPS.time >= l3_conn.l3_ip_t_s, GPS.time <= l3_conn.l3_ip_t_e).order_by(GPS.time).all()
            _add_segments(l3_conn_trace, l3_gps)

        del l3_conns

        tcp_conns = session.query(APTCPInfo.tcp_t_s, APTCPInfo.tcp_t_e).filter(APTCPInfo.tcp_t_s != None).filter(APTCPInfo.tcp_t_s >= exp.start_time, APTCPInfo.tcp_t_e <= exp.end_time).order_by(APTCPInfo.tcp_t_s).all()

        for tcp_conn in tcp_conns:
            tcp_gps = session.query(GPS).filter(GPS.time >= tcp_conn.tcp_t_s, GPS.time <= tcp_conn.tcp_t_e).order_by(GPS.time).all()
            _add_segments(tcp_conn_trace, tcp_gps)

    return exp_trace, l2_conn_trace, l3_conn_trace, tcp_conn_trace

def generate_gps_traces(session_dict, output_dir):
    for db_name, session in session_dict.items():
        traces = get_gps_traces(session)
        fnames = ["exp_trace.gpx", "l2_conn.gpx", "l3_conn.gpx", "tcp_conn.gpx"]
        fnames = [os.path.join(output_dir, db_name+"_"+x) for x in fnames]
        for i in range(4):
            t = traces[i]
            fn = fnames[i]
            with open(fn, "w") as f:
                f.write(t.to_xml())

def generate_drive_trace(session_dict, output_dir):
    for db_name, session in session_dict.items():
        traces = get_drive_trace(session)
        fnames = ["exp_trace.gpx"]
        fnames = [os.path.join(output_dir, db_name+"_"+x) for x in fnames]
        for i in range(1):
            t = traces[i]
            fn = fnames[i]
            with open(fn, "w") as f:
                f.write(t.to_xml())


def get_avgspeed_cdf(session):
    #get rid of outliers produced by GPS errors.
    infos = session.query(APTCPInfo.avg_speed).filter(APTCPInfo.avg_speed != None, APTCPInfo.avg_speed < 100).all()
    infos = (x[0] for x in infos)
    #conns = session.query(APTCPInfo.l2_conn_t_s, APTCPInfo.l2_conn_t_e).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    #infos = (__calculate_avg_driving_speed(x[0], x[1], session) for x in conns)
    #infos = filter(lambda x:x!=None, infos)
    return __get_cdf(infos)

@cdf_plotter("avg_speed_cdf"+FIG_EXT, "Avg. speed (km/h)")
def plot_avgspeed_cdf(session):
    return get_avgspeed_cdf(session)

@ccdf_plotter("avg_speed_ccdf"+FIG_EXT, "Avg. speed (km/h)")
def plot_avgspeed_ccdf(session):
    return get_avgspeed_cdf(session)

def pearson_r_plotter(plot_name, label_list):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(session_dict, output_dir):
            set_matplotlib_env()
            for db_name, session in session_dict.items():
                pr_matrix = func(session)
                plt.figure(figsize=(12, 10))
                sns.set(font_scale=1.6)
                heat_map = sns.heatmap(pr_matrix, annot=True, fmt=".2f", cmap="YlGnBu", xticklabels=label_list, yticklabels=label_list, vmin=-1, vmax=1, robust=True)
                plt.xticks(rotation=-20)
                plt.yticks(rotation=65)
                heat_map.get_figure().savefig(os.path.join(output_dir, db_name+"_"+plot_name), format=FIG_FMT, bbox_inches="tight")
                plt.clf()
        return wrapper
    return decorator

def __get_pr_matrix(arr):
    pr_matrix = np.array([[0.0]*len(arr) for i in range(len(arr))])
    for i in range(len(arr)):
        for j in range(i, len(arr)):
            #TODO: also show p-value in heatmap
            pr_matrix[i][j] = pearsonr(arr[i], arr[j])[0]
            pr_matrix[j][i] = pr_matrix[i][j]
    return pr_matrix

def get_full_pearsonr(session):
    infos = session.query(APTCPInfo.l2_conn_t_e, APTCPInfo.l2_conn_t_s, APTCPInfo.l3_ip_t_e, APTCPInfo.l3_ip_t_s, APTCPInfo.tcp_t_e, APTCPInfo.tcp_t_s, APTCPInfo.avg_speed, APTCPInfo.l2_signal_lv, APTCPInfo.l2_hs_t_e - APTCPInfo.l2_hs_t_s).filter(APTCPInfo.avg_speed != None).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()

    #l2, avg_speed, ISS, 4WHS time, has_ip, has_tcp
    arr = [[], [], [], [], [], []]
    for info in infos:
        arr[0].append(float(info.l2_conn_t_e - info.l2_conn_t_s))
        if info.l3_ip_t_s:
            #l3_val = info.l3_ip_t_e - info.l3_ip_t_s
            l3_val = 1
        else:
            l3_val = 0
        arr[4].append(float(l3_val))

        if info.tcp_t_s:
            #l4_val = info.tcp_t_e - info.tcp_t_s
            l4_val = 1
        else:
            l4_val = 0
        arr[5].append(float(l4_val))
        arr[1].append(float(info.avg_speed))
        arr[2].append(float(info.l2_signal_lv))
        arr[3].append(float(info[-1]))
    return __get_pr_matrix(arr)

def get_l3_pearsonr(session):
    infos = session.query(APTCPInfo.l2_conn_t_e, APTCPInfo.l2_conn_t_s, APTCPInfo.l3_ip_t_e, APTCPInfo.l3_ip_t_s, APTCPInfo.tcp_t_e, APTCPInfo.tcp_t_s, APTCPInfo.avg_speed, APTCPInfo.l2_signal_lv, APTCPInfo.l2_hs_t_e - APTCPInfo.l2_hs_t_s, APTCPInfo.l3_dhcp_t_e - APTCPInfo.l3_dhcp_t_s).filter(APTCPInfo.avg_speed != None, APTCPInfo.l3_ip != None).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    #l2, ip_duration, has_tcp, avg_speed, ISS, 4WHS time, DHCP time
    arr = [[], [], [], [], [], [], []]
    for info in infos:
        arr[0].append(float(info.l2_conn_t_e - info.l2_conn_t_s))
        l3_val = info.l3_ip_t_e - info.l3_ip_t_s
        arr[1].append(float(l3_val))

        if info.tcp_t_s:
            #l4_val = info.tcp_t_e - info.tcp_t_s
            l4_val = 1
        else:
            l4_val = 0
        arr[2].append(float(l4_val))
        arr[3].append(float(info.avg_speed))
        arr[4].append(float(info.l2_signal_lv))
        arr[5].append(float(info[-2]))
        arr[6].append(float(info[-1]))
    return __get_pr_matrix(arr)

def get_tcp_pearsonr(session):
    infos = session.query(APTCPInfo.l2_conn_t_e, APTCPInfo.l2_conn_t_s, APTCPInfo.l3_ip_t_e, APTCPInfo.l3_ip_t_s, APTCPInfo.tcp_t_e, APTCPInfo.tcp_t_s, APTCPInfo.avg_speed, APTCPInfo.l2_signal_lv, APTCPInfo.l2_hs_t_e - APTCPInfo.l2_hs_t_s).filter(APTCPInfo.avg_speed != None, APTCPInfo.tcp_t_s != None).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).all()
    #l2, ip_duration, tcp_duration, avg_speed, ISS, 4WHS time
    arr = [[], [], [], [], [], []]
    for info in infos:
        arr[0].append(float(info.l2_conn_t_e - info.l2_conn_t_s))
        l3_val = info.l3_ip_t_e - info.l3_ip_t_s
        arr[1].append(float(l3_val))
        l4_val = info.tcp_t_e - info.tcp_t_s
        arr[2].append(float(l4_val))
        arr[3].append(float(info.avg_speed))
        arr[4].append(float(info.l2_signal_lv))
        arr[5].append(float(info[-1]))
    return __get_pr_matrix(arr)

#@pearson_r_plotter("full_pearsonr.pdf", ["l2_conn_duration", "has_ip", "has_tcp", "avg_speed", "ISS", "4WHS_time"])
@pearson_r_plotter("full_pearsonr"+FIG_EXT, ["l2_conn_duration", "avg_speed", "ISS", "4WHS_time", "has_ip", "has_tcp"])
def plot_full_pearsonr(session):
    return get_full_pearsonr(session)

@pearson_r_plotter("l3_pearsonr"+FIG_EXT, ["l2_conn_duration", "ip_duration", "has_tcp", "avg_speed", "ISS", "4WHS_time", "DHCP time"])
def plot_l3_pearsonr(session):
    return get_l3_pearsonr(session)

@pearson_r_plotter("tcp_pearsonr"+FIG_EXT, ["l2_conn_duration", "ip_duration", "tcp_test_duration", "avg_speed", "ISS", "4WHS_time"])
def plot_tcp_pearsonr(session):
    return get_tcp_pearsonr(session)

def box_plotter(plot_name, xaxis_label, yaxis_label, x_interval=2.5):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(session_dict, output_dir):
            set_matplotlib_env()
            for db_name, session in sorted(session_dict.items()):
                y, x = func(session)
                try:
                    x_min = math.floor(float(x[0]) / x_interval) * x_interval
                except:
                    print(plot_name, func, x, y)
                    return
                curr_x = x_min

                pos_arr = [curr_x + x_interval/2]
                arr_arr = [[]]

                #clustering
                for xx, yy in zip(x, y):
                    xx, yy = float(xx), float(yy)
                    while not (curr_x <= xx < (curr_x+x_interval)):
                        curr_x += x_interval
                        pos_arr.append(curr_x + x_interval/2)
                        arr_arr.append([])
                    arr_arr[-1].append(yy)

                plt.boxplot(arr_arr, showfliers=False, notch=False, showmeans=True, manage_xticks=False, meanline=False, widths=1.5, positions=pos_arr, medianprops={"linestyle":"-", "linewidth":1}, meanprops={"marker":"D", "markeredgecolor":"green", "markerfacecolor":"none", "markeredgewidth":1, "markersize":6})
                plt.xlabel(xaxis_label)
                plt.ylabel(yaxis_label)
                plt.xlim(left=x_min)
                plt.ylim(bottom=math.floor(min(y)))
                #plt.gca().yaxis.grid(which="major")
                plt.savefig(os.path.join(output_dir, db_name+"_"+plot_name), format=FIG_FMT, bbox_inches="tight")
                plt.clf()
        return wrapper
    return decorator


def scatter_plotter(plot_name, xaxis_label, yaxis_label):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(session_dict, output_dir):
            set_matplotlib_env()
            for db_name, session in sorted(session_dict.items()):
                x, y = func(session)
                plt.scatter(x, y, clip_on=False)
                plt.xlabel(xaxis_label)
                plt.ylabel(yaxis_label)
                plt.xlim(left=math.floor(min(x)))
                plt.ylim(bottom=math.floor(min(y)))
                plt.savefig(os.path.join(output_dir, db_name+"_"+plot_name), format=FIG_FMT, bbox_inches="tight")
                plt.clf()
        return wrapper
    return decorator

def get_rel_speed_vs_l2_conn(session):
    #get rid of outliers produced by gps errors.
    data = session.query(APTCPInfo.avg_speed, APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.avg_speed != None, APTCPInfo.avg_speed < 100).order_by(APTCPInfo.avg_speed).all()
    return [x[1] for x in data], [x[0] for x in data]

def get_rel_iss_vs_l2_conn(session):
    data = session.query(APTCPInfo.l2_signal_lv, APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.l2_signal_lv != None, APTCPInfo.l2_signal_lv < 0).order_by(APTCPInfo.l2_signal_lv).all()
    return [x[1] for x in data], [x[0] for x in data]

@scatter_plotter("speed_vs_l2_duration"+FIG_EXT, "conn. duration (s)", "Avg. speed (km/h)")
def plot_rel_speed_vs_l2_conn(session):
    return get_rel_speed_vs_l2_conn(session)

@scatter_plotter("iss_vs_l2_duration"+FIG_EXT, "conn. duration (s)", "ISS (dBm)")
def plot_rel_iss_vs_l2_conn(session):
    return get_rel_iss_vs_l2_conn(session)

@box_plotter("speed_vs_l2_duration_box"+FIG_EXT,  "Avg. speed (km/h)", "conn. duration (s)")
def plot_rel_speed_vs_l2_conn_box(session):
    return get_rel_speed_vs_l2_conn(session)

@box_plotter("iss_vs_l2_duration_box"+FIG_EXT, "ISS (dBm)", "conn. duration (s)")
def plot_rel_iss_vs_l2_conn_box(session):
    return get_rel_iss_vs_l2_conn(session)

def generate_rel_freq_vs_l2_conn(session_dict, output_dir):
    for db_name, session in sorted(session_dict.items()):
        res_5g = session.query(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.l2_freq >= 5000).all()
        res_24g = session.query(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.l2_freq < 2500).all()
        res_5g = [float(x[0]) for x in res_5g]
        res_24g = [float(x[0]) for x in res_24g]
        with open(os.path.join(output_dir, db_name+"_freq_vs_l2_conn.csv"), "w") as f:
            csv_f = csv.writer(f)
            csv_f.writerow(["", "mean", "std", "median", "20th %", "80th %", "count"])
            if len(res_5g):
                line_5g = ["5G", np.mean(res_5g), np.std(res_5g), np.median(res_5g), np.percentile(res_5g, 20), np.percentile(res_5g, 80), len(res_5g)]
            else:
                line_5g = []
            if len(res_24g):
                line_24g = ["2.4G", np.mean(res_24g), np.std(res_24g), np.median(res_24g), np.percentile(res_24g, 20), np.percentile(res_24g, 80), len(res_24g)]
            else:
                line_24g = []
            csv_f.writerow(line_5g)
            csv_f.writerow(line_24g)

def deco_funcs_rel(func):
    @functools.wraps(func)
    def wrapper(session_dict, output_dir):
        if os.path.exists(os.path.join(output_dir, func.__name__)):
            os.system("rm -rf {}".format(os.path.join(output_dir, func.__name__)))
        os.system("mkdir -p {}".format(os.path.join(output_dir, func.__name__)))
        funcs = func()
        for f in funcs:
            f(session_dict, os.path.join(output_dir, func.__name__))
    return wrapper

@deco_funcs_rel
def funcs_rel_speed_vs_goodput():
    tcp_dirs = [FlowType.UPLOAD, FlowType.DOWNLOAD]
    flow_nbs = [1, 2, 4, 8, 16]
    ccs = ["cubic", "bbr"]
    funcs = []
    for tcp_dir in tcp_dirs:
        for cc in ccs:
            for flow_nb in flow_nbs:
                def func(tcp_dir, cc, flow_nb):
                    #@scatter_plotter("speed_vs_goodput_{}_{}_{}".format(tcp_dir.value, cc, flow_nb)+FIG_EXT, "Avg. {} goodput [{} x{}] (Mbit/s)".format(tcp_dir.value, cc, flow_nb), "Avg. vehicle speed (km/h)")
                    @box_plotter("speed_vs_goodput_{}_{}_{}".format(tcp_dir.value, cc, flow_nb)+FIG_EXT, "Avg. vehicle speed (km/h)", "Avg. {} goodput [{} x{}] (Mbit/s)".format(tcp_dir.value, cc, flow_nb))
                    def ret_func(session):
                        data = session.query(APTCPInfo.avg_speed, APTCPInfo.tcp_goodput_pcap, APTCPInfo.tcp_goodput_app).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.tcp_direction == tcp_dir, APTCPInfo.tcp_cc == cc, APTCPInfo.tcp_flow_nb == flow_nb, APTCPInfo.avg_speed != None).order_by(APTCPInfo.avg_speed).all()
                        if tcp_dir == FlowType.UPLOAD:
                            return [x.tcp_goodput_pcap for x in data], [x.avg_speed for x in data]
                        else:
                            return [x.tcp_goodput_app for x in data], [x.avg_speed for x in data]
                    return ret_func
                funcs.append(func(tcp_dir, cc, flow_nb))
    return funcs

@deco_funcs_rel
def funcs_rel_speed_vs_loss_rate():
    tcp_dirs = [FlowType.UPLOAD, FlowType.DOWNLOAD]
    flow_nbs = [1, 2, 4, 8, 16]
    ccs = ["cubic", "bbr"]
    funcs = []
    for tcp_dir in tcp_dirs:
        for cc in ccs:
            for flow_nb in flow_nbs:
                def func(tcp_dir, cc, flow_nb):
                    #@scatter_plotter("speed_vs_goodput_{}_{}_{}".format(tcp_dir.value, cc, flow_nb)+FIG_EXT, "Avg. {} goodput [{} x{}] (Mbit/s)".format(tcp_dir.value, cc, flow_nb), "Avg. vehicle speed (km/h)")
                    @box_plotter("speed_vs_pktloss_{}_{}_{}".format(tcp_dir.value, cc, flow_nb)+FIG_EXT, "Avg. vehicle speed (km/h)", "{} loss rate [{} x{}] (%)".format(tcp_dir.value, cc, flow_nb))
                    def ret_func(session):
                        data = session.query(APTCPInfo.avg_speed, APTCPInfo.tcp_loss_rate).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.tcp_direction == tcp_dir, APTCPInfo.tcp_cc == cc, APTCPInfo.tcp_flow_nb == flow_nb, APTCPInfo.avg_speed != None, APTCPInfo.tcp_loss_rate != None).order_by(APTCPInfo.avg_speed).all()
                        return [x.tcp_loss_rate * 100 for x in data], [x.avg_speed for x in data]
                    return ret_func
                funcs.append(func(tcp_dir, cc, flow_nb))
    return funcs

@deco_funcs_rel
def funcs_rel_l2_duration_vs_goodput():
    tcp_dirs = [FlowType.UPLOAD, FlowType.DOWNLOAD]
    flow_nbs = [1, 2, 4, 8, 16]
    ccs = ["cubic", "bbr"]
    funcs = []
    for tcp_dir in tcp_dirs:
        for cc in ccs:
            for flow_nb in flow_nbs:
                def func(tcp_dir, cc, flow_nb):
                    #@scatter_plotter("l2_duration_vs_goodput_{}_{}_{}".format(tcp_dir.value, cc, flow_nb)+FIG_EXT, "Avg. {} goodput [{} x{}] (Mbit/s)".format(tcp_dir.value, cc, flow_nb), "Link-layer connectivity duration (s)")
                    @box_plotter("l2_duration_vs_goodput_{}_{}_{}".format(tcp_dir.value, cc, flow_nb)+FIG_EXT, "Link-layer conn. duration (s)", "Avg. {} goodput [{} x{}] (Mbit/s)".format(tcp_dir.value, cc, flow_nb))
                    def ret_func(session):
                        data = session.query(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s, APTCPInfo.tcp_goodput_pcap, APTCPInfo.tcp_goodput_app).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.tcp_direction == tcp_dir, APTCPInfo.tcp_cc == cc, APTCPInfo.tcp_flow_nb == flow_nb).order_by(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s).all()
                        if tcp_dir == FlowType.UPLOAD:
                            return [x.tcp_goodput_pcap for x in data], [x[0] for x in data]
                        else:
                            return [x.tcp_goodput_app for x in data], [x[0] for x in data]
                    return ret_func
                funcs.append(func(tcp_dir, cc, flow_nb))
    return funcs

@deco_funcs_rel
def funcs_rel_tcp_duration_vs_goodput():
    tcp_dirs = [FlowType.UPLOAD, FlowType.DOWNLOAD]
    flow_nbs = [1, 2, 4, 8, 16]
    ccs = ["cubic", "bbr"]
    funcs = []
    for tcp_dir in tcp_dirs:
        for cc in ccs:
            for flow_nb in flow_nbs:
                def func(tcp_dir, cc, flow_nb):
                    #@scatter_plotter("tcp_duration_vs_goodput_{}_{}_{}".format(tcp_dir.value, cc, flow_nb)+FIG_EXT, "Avg. {} goodput [{} x{}] (Mbit/s)".format(tcp_dir.value, cc, flow_nb), "TCP connectivity duration (s)")
                    @box_plotter("tcp_duration_vs_goodput_{}_{}_{}".format(tcp_dir.value, cc, flow_nb)+FIG_EXT, "TCP connectivity duration (s)", "Avg. {} goodput [{} x{}] (Mbit/s)".format(tcp_dir.value, cc, flow_nb))
                    def ret_func(session):
                        data = session.query(APTCPInfo.tcp_t_e - APTCPInfo.tcp_t_s, APTCPInfo.tcp_goodput_pcap, APTCPInfo.tcp_goodput_app).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.tcp_direction == tcp_dir, APTCPInfo.tcp_cc == cc, APTCPInfo.tcp_flow_nb == flow_nb).order_by(APTCPInfo.tcp_t_e - APTCPInfo.tcp_t_s).all()
                        if tcp_dir == FlowType.UPLOAD:
                            return [x.tcp_goodput_pcap for x in data], [x[0] for x in data]
                        else:
                            return [x.tcp_goodput_app for x in data], [x[0] for x in data]
                    return ret_func
                funcs.append(func(tcp_dir, cc, flow_nb))
    return funcs

@deco_funcs_rel
def funcs_rel_iss_vs_loss_rate():
    tcp_dirs = [FlowType.UPLOAD, FlowType.DOWNLOAD]
    flow_nbs = [1, 2, 4, 8, 16]
    ccs = ["cubic", "bbr"]
    funcs = []
    for tcp_dir in tcp_dirs:
        for cc in ccs:
            for flow_nb in flow_nbs:
                def func(tcp_dir, cc, flow_nb):
                    #@scatter_plotter("iss_vs_goodput_{}_{}_{}".format(tcp_dir.value, cc, flow_nb)+FIG_EXT, "Avg. {} goodput [{} x{}] (Mbit/s)".format(tcp_dir.value, cc, flow_nb), "ISS (dBm)")
                    @box_plotter("iss_vs_loss_rate_{}_{}_{}".format(tcp_dir.value, cc, flow_nb)+FIG_EXT, "ISS (dBm)", "{} loss rate [{} x{}] (%)".format(tcp_dir.value, cc, flow_nb))
                    def ret_func(session):
                        data = session.query(APTCPInfo.l2_signal_lv, APTCPInfo.tcp_loss_rate).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.tcp_direction == tcp_dir, APTCPInfo.tcp_cc == cc, APTCPInfo.tcp_flow_nb == flow_nb, APTCPInfo.l2_signal_lv != None, APTCPInfo.l2_signal_lv < 0, APTCPInfo.tcp_loss_rate != None).order_by(APTCPInfo.l2_signal_lv).all()
                        return [x.tcp_loss_rate * 100 for x in data], [x[0] for x in data]
                    return ret_func
                funcs.append(func(tcp_dir, cc, flow_nb))
    return funcs

@deco_funcs_rel
def funcs_rel_iss_vs_goodput():
    tcp_dirs = [FlowType.UPLOAD, FlowType.DOWNLOAD]
    flow_nbs = [1, 2, 4, 8, 16]
    ccs = ["cubic", "bbr"]
    funcs = []
    for tcp_dir in tcp_dirs:
        for cc in ccs:
            for flow_nb in flow_nbs:
                def func(tcp_dir, cc, flow_nb):
                    #@scatter_plotter("iss_vs_goodput_{}_{}_{}".format(tcp_dir.value, cc, flow_nb)+FIG_EXT, "Avg. {} goodput [{} x{}] (Mbit/s)".format(tcp_dir.value, cc, flow_nb), "ISS (dBm)")
                    @box_plotter("iss_vs_goodput_{}_{}_{}".format(tcp_dir.value, cc, flow_nb)+FIG_EXT, "ISS (dBm)", "Avg. {} goodput [{} x{}] (Mbit/s)".format(tcp_dir.value, cc, flow_nb))
                    def ret_func(session):
                        data = session.query(APTCPInfo.l2_signal_lv, APTCPInfo.tcp_goodput_pcap, APTCPInfo.tcp_goodput_app).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.tcp_direction == tcp_dir, APTCPInfo.tcp_cc == cc, APTCPInfo.tcp_flow_nb == flow_nb, APTCPInfo.l2_signal_lv != None, APTCPInfo.l2_signal_lv < 0).order_by(APTCPInfo.l2_signal_lv).all()
                        if tcp_dir == FlowType.UPLOAD:
                            return [x.tcp_goodput_pcap for x in data], [x[0] for x in data]
                        else:
                            return [x.tcp_goodput_app for x in data], [x[0] for x in data]
                    return ret_func
                funcs.append(func(tcp_dir, cc, flow_nb))
    return funcs

def generate_rel_freq_vs_goodput(session_dict, output_dir):
    for db_name, session in sorted(session_dict.items()):
        tcp_dirs = [FlowType.UPLOAD, FlowType.DOWNLOAD]
        flow_nbs = [1, 2, 4, 8, 16]
        ccs = ["cubic", "bbr"]
        with open(os.path.join(output_dir, db_name+"_freq_vs_goodput.csv"), "w") as f:
            csv_f = csv.writer(f)
            csv_f.writerow(["", "", "", "", "mean", "std", "median", "20th %", "80th %", "count"])
            for tcp_dir in tcp_dirs:
                for cc in ccs:
                    for flow_nb in flow_nbs:
                        res_5g = session.query(APTCPInfo.tcp_goodput_pcap, APTCPInfo.tcp_goodput_app).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.tcp_direction == tcp_dir, APTCPInfo.tcp_cc == cc, APTCPInfo.tcp_flow_nb == flow_nb, APTCPInfo.l2_freq >= 5000).all()
                        res_24g = session.query(APTCPInfo.tcp_goodput_pcap, APTCPInfo.tcp_goodput_app).filter(APTCPInfo.l2_conn_t_e - APTCPInfo.l2_conn_t_s <= MAX_CONN_LEN).filter(APTCPInfo.tcp_direction == tcp_dir, APTCPInfo.tcp_cc == cc, APTCPInfo.tcp_flow_nb == flow_nb, APTCPInfo.l2_freq < 2500).all()
                        if tcp_dir == FlowType.UPLOAD:
                            res_5g = [float(x.tcp_goodput_pcap) for x in res_5g]
                            res_24g = [float(x.tcp_goodput_pcap) for x in res_24g]
                        else:
                            res_5g = [float(x.tcp_goodput_app) for x in res_5g]
                            res_24g = [float(x.tcp_goodput_app) for x in res_24g]

                        if len(res_5g) > 0:
                            line_5g = [tcp_dir.value, cc, flow_nb, "5G", np.mean(res_5g), np.std(res_5g), np.median(res_5g), np.percentile(res_5g, 20), np.percentile(res_5g, 80), len(res_5g)]
                        else:
                            line_5g = []
                        if len(res_24g) > 0:
                            line_24g = [tcp_dir.value, cc, flow_nb, "2.4G", np.mean(res_24g), np.std(res_24g), np.median(res_24g), np.percentile(res_24g, 20), np.percentile(res_24g, 80), len(res_24g)]
                        else:
                            line_24g = []

                        csv_f.writerow(line_5g)
                        csv_f.writerow(line_24g)
                        csv_f.writerow([])

def _parallized_plotting(inner_func):
    session_dict = {}
    plt.ioff()
    for label_name, real_name in DB_NAMES.items():
        db = DBOperator(DB_USER, DB_PSW, DB_HOST, DB_PORT, real_name)
        session_dict[label_name] = db.get_session()
    inner_func(session_dict, args.output_dir)

def _special_plot_ip_changing_by_ssid(ssid_dict):
    session_dict = {}
    plt.ioff()
    for label_name, real_name in DB_NAMES.items():
        db = DBOperator(DB_USER, DB_PSW, DB_HOST, DB_PORT, real_name)
        session_dict[label_name] = db.get_session()
    #plot_ip_changing_by_ssid(session_dict, args.output_dir, ssid_dict)
    generate_ip_changing_data(session_dict, args.output_dir, ssid_dict)


def plot_connectivity_results():
    global DB_NAMES
    #DB_NAMES = {"LA":"carfi_la", "OldLA":"carfi_oldla"}
    DB_NAMES = {"LA":"carfi_la", "Macao":"carfi_macau", "Paris":"carfi_paris", "Bologna":"carfi_bologna"}
    #DB_NAMES = {"ParisStatic": "carfi_homerand2_paris"}
    #DB_NAMES = {"Paris38": "carfi_paris"}
    #DB_NAMES = {"LA": "carfi_oldla"}

    global PLOT_CYCLER
    PLOT_CYCLER = LMP_PLOT_CYCLER

    pending_tasks = []

    pending_tasks += [plot_ratio_of_tcp_vs_whole, plot_assoc_setup_overhead_breakdown]
    #pending_tasks += [plot_avgspeed_cdf]
    pending_tasks += [plot_avgspeed_ccdf]
    #pending_tasks += [plot_inter_conn_avg_speed_cdf]

    pending_tasks += [plot_l2_overall_assoc_duration_cdf]
    pending_tasks += [plot_dhcp_duration_cdf]
    pending_tasks += [plot_until_ip_time_cdf]

    #pending_tasks += [plot_l2_conn_duration_cdf, plot_ip_duration_cdf]
    pending_tasks += [plot_l2_conn_duration_ccdf, plot_ip_duration_ccdf]

    pending_tasks += [plot_inter_ap_duration_cdf, plot_inter_ip_duration_cdf]

    pending_tasks += [plot_ip_changing]
    pending_tasks += [plot_ap_coverage_m_cdf]

    pending_tasks += [plot_rel_speed_vs_l2_conn, plot_rel_iss_vs_l2_conn]
    pending_tasks += [plot_rel_speed_vs_l2_conn_box, plot_rel_iss_vs_l2_conn_box]
    pending_tasks += [plot_l2_ap_signal_cdf]
    pending_tasks += [generate_rel_freq_vs_l2_conn]
    pending_tasks += [output_freq_change_per_ap]

    return pending_tasks

def plot_tcp_results():
    global DB_NAMES
    #DB_NAMES = {"LA":"carfi_la"}
    DB_NAMES = {"LA":"carfi_la", "Macao":"carfi_macau", "Paris":"carfi_paris", "Bologna":"carfi_bologna"}
    #DB_NAMES = {"Macao(M)":"carfi_macau2macau", "Macao(S)": "carfi_macau", "Paris":"carfi_paris"}
    #DB_NAMES = {"ParisStatic": "carfi_homerand2_paris"}
    #DB_NAMES = {"Paris38": "carfi_paris"}

    global PLOT_CYCLER
    PLOT_CYCLER = MMP_PLOT_CYCLER

    pending_tasks = []

    pending_tasks += [plot_ip_to_tcp_time_cdf]
    pending_tasks += [plot_until_tcp_time_cdf]
    pending_tasks += [plot_inter_tcp_duration_cdf]

    pending_tasks += [plot_tcp_duration_ccdf]
    pending_tasks += [plot_overall_tcp_download_goodput_ccdf, plot_overall_tcp_upload_goodput_ccdf]
    pending_tasks += [plot_download_volume_per_ap_ccdf, plot_upload_volume_per_ap_ccdf]
    pending_tasks += [plot_tcp_avg_goodput_ccdf, plot_tcp_avg_goodput_nofn_ccdf]

    #pending_tasks += [plot_tcp_duration_cdf]
    #pending_tasks += [plot_tcp_avg_goodput_cdf, plot_tcp_avg_goodput_nofn_cdf]
    #pending_tasks += [plot_download_volume_per_ap_cdf, plot_upload_volume_per_ap_cdf]
    #pending_tasks += [plot_overall_tcp_download_goodput_cdf, plot_overall_tcp_upload_goodput_cdf]

    # pending_tasks += [funcs_rel_speed_vs_goodput]
    # pending_tasks += [funcs_rel_l2_duration_vs_goodput]
    # pending_tasks += [funcs_rel_tcp_duration_vs_goodput]
    # pending_tasks += [funcs_rel_iss_vs_goodput]
    # pending_tasks += [funcs_rel_speed_vs_loss_rate]
    # pending_tasks += [funcs_rel_iss_vs_loss_rate]
    #pending_tasks += [generate_rel_freq_vs_goodput]

    return pending_tasks

def plot_tcp_correlations():
    global DB_NAMES
    #DB_NAMES = {"LA":"carfi_la"}
    DB_NAMES = {"LA":"carfi_pktloss_la", "Macao":"carfi_pktloss_macau", "Paris":"carfi_pktloss_paris", "Bologna":"carfi_pktloss_bologna"}
    #DB_NAMES = {"Macao(M)":"carfi_macau2macau", "Macao(S)": "carfi_macau", "Paris":"carfi_paris"}
    #DB_NAMES = {"ParisStatic": "carfi_homerand2_paris"}
    #DB_NAMES = {"Paris38": "carfi_paris"}

    global PLOT_CYCLER
    PLOT_CYCLER = MMP_PLOT_CYCLER

    pending_tasks = []

    pending_tasks += [funcs_rel_speed_vs_loss_rate]
    pending_tasks += [funcs_rel_iss_vs_loss_rate]

    return pending_tasks

def main():
    if not os.path.exists(args.output_dir):
        os.mkdir(args.output_dir)

    pending_tasks = []

    pending_tasks += [output_dataset_overview]

    #GPS traces ------------
    #global DB_NAMES
    #SSID_DICT = {"Bologna":["%WOW%", "%Emilia%", "%ALMAWIFI%"], "Paris":["%Free%"], "LA":["%Spectrum%", "%CableWiFi%", "%TWCWiFi%", "%eduroam%"], "Macao":["%CTM%"]}
    #DB_NAMES = {"LA":"carfi_la", "Macao":"carfi_macau", "Paris":"carfi_paris", "Bologna":"carfi_bologna"}
    #_special_plot_ip_changing_by_ssid(SSID_DICT)
    #DB_NAMES = {"Macao(M)":"carfi_macau2macau", "Macao(S)": "carfi_macau", "Paris":"carfi_paris"}
    #DB_NAMES = {"LA":"carfi_la", "Macao":"carfi_macau", "Paris":"carfi_paris"}
    #DB_NAMES = {"Macao(M)":"carfi_macau2macau", "Macao(S)": "carfi_macau", "Paris":"carfi_paris", "Macao": "carfi_macau_merged", "LA": "carfi_oldla"}
    #DB_NAMES = {"LA":"carfi_la_fails"}
    #DB_NAMES = {"Bologna":"carfi_bologna"}
    #pending_tasks += [generate_gps_traces]
    #pending_tasks += [generate_drive_trace]
    #pending_tasks += [output_dhcp_server_info]

    #global DB_NAMES
    #DB_NAMES = {"Paris":"carfi_paris", "Macao": "carfi_macau_merged", "LA": "carfi_oldla", "Bologna": "carfi_bologna"}
    #global PLOT_CYCLER
    #PLOT_CYCLER = LMP_PLOT_CYCLER
    #pending_tasks += [plot_ap_coverage_m_cdf]

    #Connecivity Plots
    pending_tasks += plot_connectivity_results()

    # TCP Results
    #pending_tasks += plot_tcp_results()

    # TCP correlations
    #pending_tasks += plot_tcp_correlations()

    #Others --------------------------
    #pending_tasks += [plot_full_pearsonr]
    #pending_tasks += [plot_l3_pearsonr, plot_tcp_pearsonr]
    #pending_tasks += [plot_all_freq_dist, plot_ip_freq_dist, plot_tcp_freq_dist, plot_ap_assoc_type_dist]
    #pending_tasks += [plot_l2_auth_duration_cdf, plot_l2_assoc_duration_cdf, plot_l2_hs_duration_cdf]

    mp = Pool()
    mp.map(_parallized_plotting, pending_tasks)
    mp.close()
    mp.join()


if __name__ == "__main__":
    main()
