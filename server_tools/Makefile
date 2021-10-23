.PHONY: all clean install uninstall distclean install_tcpserver install_analyzer install_all

sub_dirs:=tester data_uploader systemd-conf analyzer

all:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir ; done

clean:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done

distclean:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done

install:
	@echo "Please specify which component you want to install by following commands:"
	@echo "    install tcp testing server: make install_tcpserver"
	@echo "    install data uploader server and analyzer: make install_analyzer"
	@echo "    install everything: make install_all"

install_all install_tcpserver install_analyzer:
	$(MAKE) -C systemd-conf $@

uninstall:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done
