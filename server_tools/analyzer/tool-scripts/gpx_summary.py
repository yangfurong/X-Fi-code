#!/usr/bin/env python3

import gpxpy
import gpxpy.gpx
import os, sys


def main():
    gpx_f = open(sys.argv[1], "r")
    gpx_hdl = gpxpy.parse(gpx_f)

    #secs
    duration = gpx_hdl.get_duration()
    #meters
    length = gpx_hdl.length_3d()
    avg_speed = length / 1000 / (duration / 3600)

    hour = duration // 3600
    duration = duration % 3600
    minute = duration // 60
    secs = duration % 60
    print("Duration: {}h{}m{}s".format(hour, minute, secs))
    print("distance: {} km".format(length / 1000))
    print("speed: {} km/h".format(avg_speed))

if __name__ == "__main__":
    main()
