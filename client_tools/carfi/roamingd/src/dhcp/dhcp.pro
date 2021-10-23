TEMPLATE = lib
TARGET = roamingd-dhcp

CONFIG += staticlib thread
CONFIG -= qt

include(../defines.pri)

INCLUDEPATH += ../basic

HEADERS = \
	dhcp6-internal.h \
	dhcp6-lease-internal.h \
	dhcp6-protocol.h \
	dhcp-identifier.h \
	dhcp-internal.h \
	dhcp-lease-internal.h \
	dhcp-protocol.h \
	dhcp-server-internal.h \
	icmp6-util.h \
	network-internal.h \
	sd-dhcp6-client.h \
	sd-dhcp6-lease.h \
	sd-dhcp-client.h \
	sd-dhcp-lease.h \
	sd-dhcp-server.h \
	sd-ndisc.h

SOURCES = \
	dhcp6-network.c \
	dhcp6-option.c \
	dhcp-identifier.c \
	dhcp-network.c \
	dhcp-option.c \
	dhcp-packet.c \
	icmp6-util.c \
	network-internal.c \
	sd-dhcp6-client.c \
	sd-dhcp6-lease.c \
	sd-dhcp-client.c \
	sd-dhcp-lease.c \
	sd-dhcp-server.c \
	sd-ndisc.c
