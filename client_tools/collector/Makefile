.PHONY: all clean install uninstall distclean

DIR:=$(shell pwd)
ROOT_PATH:=$(shell dirname $(DIR))

all:
	sed -i 's:ROOT_PATH = .*:ROOT_PATH = "$(ROOT_PATH)":g' collector_daemon	

clean install uninstall distclean:
