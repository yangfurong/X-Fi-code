#!/usr/bin/python3

import json, sys
import numpy as np

with open(sys.argv[1], "r") as f:
    data = json.load(f)
    for ssid, trips in data.items():
        print("ssid {}".format(ssid))
        ssid_ip_changed = 0
        ssid_ip_duration_list = []
        ssid_trip_duration = []
        #skip all trips without any IP connectivity
        for trip in trips:
            trip_t_s, trip_t_e, ip_list = trip
            changed = False
            last_ip = None
            curr_ip_t_s = 0
            curr_ip_t_e = 0
            ip_duration_list = []
            if len(ip_list) == 0:
                continue
            for ip, ip_t_s, ip_t_e in ip_list:
                if last_ip == None:
                    last_ip = ip
                    curr_ip_t_s = ip_t_s
                if last_ip != ip:
                    changed = True
                    ip_duration_list.append(curr_ip_t_e - curr_ip_t_s)
                    curr_ip_t_s = ip_t_s
                curr_ip_t_e = ip_t_e
                last_ip = ip
            ip_duration_list.append(curr_ip_t_e - curr_ip_t_s)
            #print(changed, trip_t_e - trip_t_s, len(ip_list), np.mean(ip_duration_list), np.std(ip_duration_list))
            if changed:
                ssid_ip_changed += 1
            ssid_ip_duration_list += ip_duration_list
            ssid_trip_duration.append(trip_t_e - trip_t_s)
        print(sorted(ssid_ip_duration_list))
        print("duration: mean {} std {}, changed: {}/{}, trip: mean {} std {}".format(np.mean(ssid_ip_duration_list), np.std(ssid_ip_duration_list), ssid_ip_changed, len(ssid_trip_duration), np.mean(ssid_trip_duration), np.std(ssid_trip_duration)))

