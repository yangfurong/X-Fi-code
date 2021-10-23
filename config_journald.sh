#!/bin/bash

Storage=`egrep "^Storage=.*$" /etc/systemd/journald.conf`
MaxUse=`egrep "^SystemMaxUse=.*$" /etc/systemd/journald.conf`
MaxUsePercent="1024M"

if [ -z $Storage ]; then
    echo "Storage=persistent" >> /etc/systemd/journald.conf
else
    sed -i "s:^Storage=.*$:Storage=persistent:g" /etc/systemd/journald.conf
fi

if [ -z $MaxUse ]; then
    echo "SystemMaxUse=$MaxUsePercent" >> /etc/systemd/journald.conf
else
    sed -i "s:^SystemMaxUse=.*$:SystemMaxUse=$MaxUsePercent:g" /etc/systemd/journald.conf
fi

systemctl restart systemd-journald.service
