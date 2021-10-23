PROG=tcp_client
CC=gcc
CFLAGS=-O3
LDFLAGS=-lpthread

.PHONY: clean distclean

$(PROG): client.o
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	-rm -f *.o $(PROG)

distclean:
	-rm -f *.o $(PROG)
