PROG=tcp_server
CC=gcc
CFLAGS=-O3
LDFLAGS=-lpthread
DIR=$(shell pwd)

.PHONY: clean distclean all install uninstall

all: $(PROG) daemon

daemon:
	sed -i 's:RT_PATH=.*:RT_PATH="$(DIR)":g' tcp_server_daemon

$(PROG): server.o
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	-rm -f *.o $(PROG)

distclean:
	-rm -f *.o $(PROG)

install uninstall:
