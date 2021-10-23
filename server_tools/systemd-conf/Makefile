.PHONY: clean install uninstall all distclean install_tcpserver install_analyzer install_all

p_dir=$(shell cd .. && pwd)
tcpserver=$(p_dir)/tester/tcp_server_daemon
analyzer=$(p_dir)/analyzer/analyzer_daemon
uploader_server=$(p_dir)/data_uploader/uploader_server_daemon

all:
	sed -i 's:ExecStart=.*:ExecStart=$(tcpserver):g' carfi-tcpserver.service
	sed -i 's:ExecStart=.*:ExecStart=$(analyzer):g' carfi-analyzer.service
	sed -i 's:ExecStart=.*:ExecStart=$(uploader_server):g' carfi-uploader-server.service

clean distclean install:

install_all:
	cp carfi-tcpserver.service /lib/systemd/system/
	cp carfi-uploader-server.service /lib/systemd/system/
	cp carfi-analyzer.service /lib/systemd/system/
	systemctl enable carfi-tcpserver.service
	systemctl enable carfi-uploader-server.service
	systemctl enable carfi-analyzer.service
	
install_tcpserver:
	cp carfi-tcpserver.service /lib/systemd/system/
	systemctl enable carfi-tcpserver.service

install_analyzer:
	cp carfi-uploader-server.service /lib/systemd/system/
	cp carfi-analyzer.service /lib/systemd/system/
	systemctl enable carfi-uploader-server.service
	systemctl enable carfi-analyzer.service

uninstall:
	-systemctl disable carfi-analyzer.service
	-systemctl disable carfi-uploader-server.service
	-systemctl disable carfi-tcpserver.service
	-rm /lib/systemd/system/carfi-analyzer.service
	-rm /lib/systemd/system/carfi-uploader-server.service
	-rm /lib/systemd/system/carfi-tcpserver.service
