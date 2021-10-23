.PHONY: all clean install uninstall distclean

DIR:=$(shell pwd)

all:
	sed -i 's:ROOT_PATH=.*:ROOT_PATH="$(DIR)":g' analyzer_daemon

clean install uninstall distclean:
