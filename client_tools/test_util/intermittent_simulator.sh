#!/bin/bash

#This function generate a random number from [min, max]
function rand() {
    min=$1
    max=$(($2-$min+1))
    num=$(($RANDOM+10000000000))
    num=$(($num%$max+$min))
    echo $num
}

function simulator_start() {
    device=$1
    while true; do
        sec=$(rand 10 20)
        sudo iw dev $device disconnect
        echo "next disassociation in $sec seconds"
        sleep $sec      
    done
}

simulator_start $1
