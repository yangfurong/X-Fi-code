TEMPLATE = app
TARGET = roamingd

CONFIG += thread use_c_linker
CONFIG -= qt

include(../defines.pri)

INCLUDEPATH += ../dhcp ../netlink ../basic
LIBS += \
    -L../dhcp -lroamingd-dhcp \
    -L../netlink -lroamingd-netlink \
    -L../basic -lroamingd-basic \
    -lrt

HEADERS = \
    roamingd-address.h \
    roamingd-address-pool.h \
    roamingd-link.h \
    roamingd-manager.h \
    roamingd-netdev.h \
    roamingd-network.h \
    roamingd-route.h \
    roamingd-util.h

SOURCES = \
    main.c \
    roamingd-address.c \
    roamingd-address-pool.c \
    roamingd-dhcp4.c \
    roamingd-dhcp6.c \
    roamingd-link.c \
    roamingd-manager.c \
    roamingd-ndisc.c \
    roamingd-network.c \
    roamingd-route.c \
    roamingd-util.c
