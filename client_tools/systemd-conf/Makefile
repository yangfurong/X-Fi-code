.PHONY: clean install uninstall all distclean

p_dir=$(shell cd .. && pwd)
collector=$(p_dir)/collector/collector_daemon
uploader=$(p_dir)/data_uploader/uploader_client_daemon

all:
	sed -i 's:ExecStart=.*:ExecStart=$(collector):g' carfi-data-collector.service
	sed -i 's:ExecStart=.*:ExecStart=$(uploader):g' carfi-uploader-client.service

clean distclean:
	
install:
	cp carfi-data-collector.service carfi-uploader-client.service /lib/systemd/system/
	systemctl enable carfi-data-collector.service
	systemctl enable carfi-uploader-client.service

uninstall:
	systemctl disable carfi-uploader-client.service
	systemctl disable carfi-data-collector.service
	rm /lib/systemd/system/carfi-data-collector.service
	rm /lib/systemd/system/carfi-uploader-client.service
