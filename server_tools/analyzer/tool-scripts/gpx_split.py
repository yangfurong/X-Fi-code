#!/usr/bin/env python3

import gpxpy
import gpxpy.gpx
import os, sys
import shlex, subprocess

#Size Limit (5MB)
SIZE_LMT = 5*1024*1024

def split_gpx(input_f):
    gpx_f = open(input_f, "r")
    gpx_hdl = gpxpy.parse(gpx_f)

    gpx_new = gpxpy.gpx.GPX()
    gpx_new.tracks.append(gpxpy.gpx.GPXTrack())

    #for the moment, I only consider the gpx file has one track
    segments = gpx_hdl.tracks[0].segments
    fh_segments = segments[:len(segments)//2]
    sh_segments = segments[len(segments)//2:]

    gpx_new.tracks[0].segments = sh_segments
    gpx_hdl.tracks[0].segments = fh_segments

    f_name, f_ext = os.path.splitext(input_f)

    fh_path = f_name+"1"+f_ext
    sh_path = f_name+"2"+f_ext

    fh_f = open(fh_path, "w")
    sh_f = open(sh_path, "w")
    fh_f.write(gpx_hdl.to_xml())
    sh_f.write(gpx_new.to_xml())

    fh_f.flush()
    fh_f.close()
    sh_f.flush()
    sh_f.close()

    gpx_f.close()
    subprocess.call(shlex.split("rm {}".format(input_f)))

def main():
    #The original input file will be removed, please use a copy of that
    input_dir = sys.argv[1]
    more_files = True
    while more_files:
        more_files = False
        for f_name in os.listdir(input_dir):
            f_path = os.path.join(input_dir, f_name)
            if os.path.getsize(f_path) >= SIZE_LMT:
                split_gpx(f_path)
                more_files = True

if __name__ == "__main__":
    main()
