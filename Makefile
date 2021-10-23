.PHONY: all clean install uninstall distclean

sub_dirs:=client_tools server_tools

all:
	@echo "please enter client_tools and/or server_tools to 'make' client parts and/or server parts separatedly"

clean:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done

distclean:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done

install:
	@echo "please enter client_tools and/or server_tools to 'make install' client parts and/or server parts separatedly"

uninstall:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done
