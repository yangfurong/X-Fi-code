.PHONY: all clean install uninstall distclean

sub_dirs:=roamingd tester

all:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir ; done

clean:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done

distclean:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done

install:
	cp roamingd/hostap/wpa_supplicant/wpa_supplicant bin/wpa_supplicant
	cp roamingd/src/roamingd/roamingd bin/roamingd
	cp tester/tester_initiator.py bin/tester_initiator
	cp tester/tcp_client bin/tcp_client

uninstall:
