#!/bin/bash

has_time=`egrep "^net.ipv4.tcp_keepalive_time" /etc/sysctl.conf`
has_probes=`egrep "^net.ipv4.tcp_keepalive_probes" /etc/sysctl.conf`
has_intvl=`egrep "^net.ipv4.tcp_keepalive_intvl" /etc/sysctl.conf`

keepalive_time=540
keepalive_probes=2
keepalive_intvl=60

if [ -z $has_time ]; then
    echo "net.ipv4.tcp_keepalive_time=$keepalive_time" >> /etc/sysctl.conf
else
    sed -i "s/net\.ipv4\.tcp_keepalive_time.*/net\.ipv4\.tcp_keepalive_time=$keepalive_time/g" /etc/sysctl.conf
fi

if [ -z $has_probes ]; then
    echo "net.ipv4.tcp_keepalive_probes=$keepalive_probes" >> /etc/sysctl.conf
else
    sed -i "s/net\.ipv4\.tcp_keepalive_probes.*/net\.ipv4\.tcp_keepalive_probes=$keepalive_probes/g" /etc/sysctl.conf
fi


if [ -z $has_intvl ]; then
    echo "net.ipv4.tcp_keepalive_intvl=$keepalive_intvl" >> /etc/sysctl.conf
else
    sed -i "s/net\.ipv4\.tcp_keepalive_intvl.*/net\.ipv4\.tcp_keepalive_intvl=$keepalive_intvl/g" /etc/sysctl.conf
fi

sysctl -p
