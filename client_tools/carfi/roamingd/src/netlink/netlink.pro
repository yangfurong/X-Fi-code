TEMPLATE = lib
TARGET = roamingd-netlink

CONFIG += staticlib thread
CONFIG -= qt

include(../defines.pri)

INCLUDEPATH += ../basic

HEADERS = \
	local-addresses.h \
	netlink-internal.h \
	netlink-types.h \
	netlink-util.h \
	sd-netlink.h

SOURCES = \
	local-addresses.c \
	netlink-message.c \
	netlink-socket.c \
	netlink-types.c \
	netlink-util.c \
	rtnl-message.c \
	sd-netlink.c
