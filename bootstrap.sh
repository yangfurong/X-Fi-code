#!/bin/bash
QMAKE=/usr/lib/x86_64-linux-gnu/qt5/bin/qmake
ROAMINGD_DIR=./client_tools/carfi/roamingd
pushd $ROAMINGD_DIR
$QMAKE -makefile
popd
