#!/bin/bash

bbr_exist=`cat /etc/modules | grep tcp_bbr`

if [ -z $bbr_exist ]; then
    echo "Load BBR and enable autoload on boot"
    echo "tcp_bbr" >> /etc/modules
    modprobe tcp_bbr
else
    echo "BBR is already autoloaded on boot"
fi
