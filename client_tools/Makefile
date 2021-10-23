.PHONY: all clean install uninstall distclean

sub_dirs:=carfi collector systemd-conf data_uploader

all:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done

clean:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done

distclean:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done

install:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done

uninstall:
	@for sub_dir in $(sub_dirs); do $(MAKE) -C $$sub_dir $@; done
