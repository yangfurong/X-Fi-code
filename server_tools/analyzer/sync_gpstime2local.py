#!/usr/bin/env python3

from multiprocessing import Pool
from datetime import datetime, timezone, timedelta
import functools
import gpxpy
import gpxpy.gpx
import argparse, os, shutil
import numpy as np
import math
import subprocess, shlex

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dir", required=True, help="the directory keeping all to-be-processed tarballs")
parser.add_argument("-o", "--output_dir", required=True, help="the directory to keep all processed tarballs")
args = parser.parse_args()

def filter_offsets(day_exps):
    offsets = []
    drive = [day_exps[0]]

    for exp in day_exps[1:]:
        #the gap BTWN two consecutive tarballs should be very very small
        if (exp[1] - drive[-1][2]) <= 30:
            drive.append(exp)
        else:
            offsets.extend(drive[1:])
            drive = [exp]
    offsets.extend(drive[1:])
    offsets = filter(lambda x:x[3] != None, offsets)
    return [x[3].total_seconds() for x in offsets]

def averaging_offset_for_each_day(exp_dict):
    offset_over_day = []
    factor = 1.3
    for day, val in sorted(exp_dict.items()):
        day_exps = sorted(val, key=lambda x:x[1])
        offsets = filter_offsets(day_exps)
        if len(offsets) > 0:
            offset_over_day.append([day, np.median(offsets)])
        else:
            #if no day before the day has assigned an offset, we have no way to estimate the offset for the day
            if len(offset_over_day) == 0 or offset_over_day[-1][1] == -1:
                #we put a placeholder here, and will try to assign it a value after we get values for the coming days
                offset_over_day.append([day, -1])
            else:
                day_gap = (day - offset_over_day[-1][0]).days
                interpolation = offset_over_day[-1][1] + day_gap * factor
                offset_over_day.append([day, interpolation])
        print("#pass1", offset_over_day[-1])
    # here, we do the second pass of offset assignment for the days without being assigned offset values
    for idx in reversed(range(0, len(offset_over_day)-1)):
        if offset_over_day[idx][1] == -1:
            day_gap = (offset_over_day[idx][0] - offset_over_day[idx+1][0]).days
            offset_over_day[idx][1] = offset_over_day[idx+1][1] + day_gap * factor
        print("#pass2", offset_over_day[idx])
    return {x[0]:math.floor(x[1]) for x in offset_over_day}

def _sync_gps_time(args):
    exp, offset, output_dir = args
    with open(os.path.join(exp, "gps.log"), "r") as f:
        gpx_file = gpxpy.parse(f)
        for track in gpx_file.tracks:
            for segment in track.segments:
                for point in segment.points:
                    point.time -= timedelta(seconds=offset)

        #update gps.log
        os.system("rm -f {}".format(os.path.join(exp, "gps.log")))
        with open(os.path.join(exp, "gps.log"), "w") as wf:
            wf.write(gpx_file.to_xml())

        os.mkdir(os.path.join(exp, "data"))
        os.system("mv {} {}".format(os.path.join(exp, "gps.log"), os.path.join(exp, "data")))
        os.system("mv {} {}".format(os.path.join(exp, "roamingd.log"), os.path.join(exp, "data")))
        os.system("mv {} {}".format(os.path.join(exp, "wpa_supplicant.log"), os.path.join(exp, "data")))
        os.system("mv {} {}".format(os.path.join(exp, "tester.data"), os.path.join(exp, "data")))
        cwd = os.getcwd()
        os.chdir(exp)
        tarball_path = os.path.basename(exp)+".tar.gz"
        subprocess.call(shlex.split("tar -zcf {} {}".format(tarball_path, "data")))
        os.chdir(cwd)
        os.system("mv {} {}".format(os.path.join(exp, tarball_path), output_dir))
    os.system("rm -rf {}".format(exp))

def sync_gps_time(exp_dir, exp_dict, offset_over_day, output_dir):
    arg_list = []
    for date, val in exp_dict.items():
        offset = offset_over_day[date]
        for exp in val:
            exp_name = exp[0]
            exp_path = os.path.join(exp_dir, exp_name)
            arg_list.append((exp_path, offset, output_dir))
            print("apply offset {} to {}".format(offset, exp_path))

    mp = Pool(15)
    mp.map(_sync_gps_time, arg_list, len(arg_list)//15)
    mp.close()
    mp.join()

def clustering_exp_by_day(offset_list):
    exp_dict = {}
    for exp, offset in offset_list:
        loc_marker, exp_start_time, exp_end_time = exp.split("-")
        exp_start_time = datetime.strptime(exp_start_time, "%Y_%m_%d_%Hh%Mm%Ss%z")
        exp_end_time = datetime.strptime(exp_end_time, "%Y_%m_%d_%Hh%Mm%Ss%z")
        exp_date = exp_start_time.date()
        if exp_date not in exp_dict:
            exp_dict[exp_date] = []
        exp_dict[exp_date].append((exp, exp_start_time.timestamp(), exp_end_time.timestamp(), offset))
    return exp_dict

def _uncompress_func(tarball):
    exp_dir = tarball.rstrip(".tar.gz")
    shutil.rmtree(exp_dir, True)
    os.mkdir(exp_dir)
    os.system("tar -zxf {} -C {}".format(tarball, exp_dir))
    sub_dir = os.path.join(exp_dir, os.listdir(exp_dir)[0])
    os.system("mv {} {}".format(os.path.join(sub_dir, "*"), exp_dir))
    os.system("rm -rf {}".format(sub_dir))
    with open(os.path.join(exp_dir, "gps.log"), "r") as f:
        gpx_file = gpxpy.parse(f)
        first_p = None
        if len(gpx_file.tracks) > 0:
            if len(gpx_file.tracks[0].segments) > 0:
                if len(gpx_file.tracks[0].segments[0].points) > 0:
                    first_p = gpx_file.tracks[0].segments[0].points[0]
        offset = None if not first_p else first_p.time - gpx_file.time
    #shutil.rmtree(exp_dir, True)
    return exp_dir, offset

def uncompress_tarballs(exp_dir):
    cwd = os.getcwd()
    os.chdir(exp_dir)
    mp = Pool(15)
    tar_list = list(filter(lambda x: x.endswith(".tar.gz"), os.listdir()))
    offset_list = mp.map(_uncompress_func, tar_list, len(tar_list)//15)
    mp.close()
    mp.join()
    os.chdir(cwd)
    return offset_list

def main():
    #parallel processing to get gps time drift for every single exp
    #return tarname, offset in secs
    offset_list = uncompress_tarballs(args.dir)

    #clustering the results by day -> {day:[(tarname(without ext), start_t, end_t, offset)]}
    exp_dict = clustering_exp_by_day(offset_list)

    #calculating the average offset for each day (only using samples not being the first or last tarball of a continueous drive)
    offset_over_day = averaging_offset_for_each_day(exp_dict)

    #parallel procesing
    #fixing the GPS time for each tarball, storing the new GPX file with copies of other files into a new directory, compressing the directory to a tarball, and moving the new tarball to the output dir
    sync_gps_time(args.dir, exp_dict, offset_over_day, args.output_dir)

main()

