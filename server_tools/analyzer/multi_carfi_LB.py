#!/usr/bin/env python3

# This script is used to compare the performance from experiments where we mounted multiple carfis on a car.

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

FIG_FMT = "png"
FIG_EXT = ".png"

DB_USER = "root"
DB_PSW = "upmc75005"
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_NAMES = {"Paris1":"carfi_rand_paris", "Paris2": "carfi_rand_paris2", "Paris3": "carfi_rand_paris3"}

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output_dir", required=True, help="the folder where results will be stored")
args = parser.parse_args()

def __get_cdf(arr):
      arr = sorted(arr)
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
          #TEMP-USE: to generate customized CDF
          #if y[i] >= 0.8:
          #  return x[:i+1], y
      return x, y


def find_collision(target, candidate_list, candidate_idx, time_range):
    l_time = (target.l2_conn_t_s - time_range)
    h_time = (target.l2_conn_t_s + time_range)
    if candidate_list[candidate_idx].l2_conn_t_s <= l_time:
        #probe forward
        while candidate_idx < len(candidate_list) and candidate_list[candidate_idx].l2_conn_t_s < l_time:
            candidate_idx += 1
        while candidate_idx < len(candidate_list) and candidate_list[candidate_idx].l2_conn_t_s <= h_time:
            if target.l2_bssid == candidate_list[candidate_idx].l2_bssid:
                return True, candidate_idx
            candidate_idx += 1
    elif candidate_list[candidate_idx].l2_conn_t_s >= h_time:
        #probe back
        while candidate_idx >= 0 and candidate_list[candidate_idx].l2_conn_t_s > h_time:
            candidate_idx -= 1
        while candidate_idx >= 0 and candidate_list[candidate_idx].l2_conn_t_s >= l_time:
            if target.l2_bssid == candidate_list[candidate_idx].l2_bssid:
                return True, candidate_idx
            candidate_idx -= 1
    else:
        #probe back and forward
        idx_cache = candidate_idx
        while candidate_idx >= 0 and candidate_list[candidate_idx].l2_conn_t_s >= l_time:
            if target.l2_bssid == candidate_list[candidate_idx].l2_bssid:
                return True, candidate_idx
            candidate_idx -= 1

        candidate_idx = idx_cache
        while candidate_idx < len(candidate_list) and candidate_list[candidate_idx].l2_conn_t_s <= h_time:
            if target.l2_bssid == candidate_list[candidate_idx].l2_bssid:
                return True, candidate_idx
            candidate_idx += 1

    if candidate_idx == len(candidate_list):
        candidate_idx -= 1
    if candidate_idx == -1:
        candidate_idx += 1
    return False, candidate_idx

def cmp_carfis(session_dict, output_dir):

    query_dict = {label:session.query(APTCPInfo).order_by(APTCPInfo.l2_conn_t_s).all() for label, session in sorted(session_dict.items())}

    for k, v in query_dict.items():
        print(k, len(v))

    idx_dict = {k:0 for k in query_dict.keys()}
    target_key = sorted(idx_dict.keys())[0]
    del idx_dict[target_key]

    print(idx_dict, target_key)

    #10s
    time_range = 10
    collision_arr = []

    for target in query_dict[target_key]:
        count= 0
        for k in idx_dict.keys():
            res, idx_dict[k] = find_collision(target, query_dict[k], idx_dict[k], time_range)
            if res:
                count += 1
                print(k, target.l2_bssid, target.l2_conn_t_s, query_dict[k][idx_dict[k]].l2_bssid, query_dict[k][idx_dict[k]].l2_conn_t_s)
        collision_arr.append(count)

    print(sum(collision_arr), len(collision_arr))

    x, y = __get_cdf(collision_arr)

    matplotlib.style.use("classic")
    plt.step(x, y, where="post")
    plt.ylim(0, 1)
    plt.xlabel("Number of other CarFis connecting with the same AP")
    plt.ylabel("CDF")
    plt.grid()
    plt.savefig(os.path.join(output_dir, "Rand_LB.png"), format=FIG_FMT)
    plt.close()

def _parallized_plotting(inner_func):
    session_dict = {}
    plt.ioff()
    for label_name, real_name in DB_NAMES.items():
        db = DBOperator(DB_USER, DB_PSW, DB_HOST, DB_PORT, real_name)
        session_dict[label_name] = db.get_session()
    inner_func(session_dict, args.output_dir)

def main():
    if not os.path.exists(args.output_dir):
        os.mkdir(args.output_dir)
    pending_tasks = [cmp_carfis]
    mp = Pool()
    mp.map(_parallized_plotting, pending_tasks, 1)
    mp.close()
    mp.join()

if __name__ == "__main__":
    main()
