TEMPLATE = app
TARGET = apscanner

CONFIG -= qt

CONFIG += link_pkgconfig
PKGCONFIG += libnl-genl-3.0

QMAKE_CFLAGS += \
    -Wall \
    -Wextra \
    -Wendif-labels \
    -Wfloat-equal \
    -Wformat=2 \
    -Winit-self \
    -Wlogical-op \
    -Wmissing-prototypes \
    -Wnested-externs \
    -Wold-style-definition \
    -Wshadow \
    -Wstrict-prototypes \
    -Wundef \
    -Wno-missing-field-initializers \
    -Wno-unused-parameter \
    -Werror=implicit-function-declaration \
    -Werror=overflow \
    -fno-common \
    -fno-strict-aliasing

HEADERS = \
    ieee80211.h \
    iw.h \
    nl80211.h

SOURCES = \
    event.c \
    genl.c \
    main.c \
    reason.c \
    reg.c \
    scan.c \
    status.c \
    util.c
