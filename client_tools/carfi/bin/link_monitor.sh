#!/bin/bash

log_f=""
intf=""

while [ "$1" != "" ] ;
do
    case $1 in
        -f) log_f=$2; shift 2 ;;
        *) intf=$1; shift 1 ;;
    esac
done


while true; do
    iwconfig $intf | ts %.s >> $log_f
    sleep 0.1
done
