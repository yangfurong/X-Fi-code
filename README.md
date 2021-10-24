# X-Fi & X-Perf  

The toolset is designed to measure TCP performance over vehicular WiFi conenctivity. It includes client-side tools and server-side tools. 

The client-side tools are responsible for automatically launching WiFi software stack, TCP measurement application, and collecting data which include GPS data, WiFi association logs, DHCP logs, TCP application logs, and pcap files.
The server-side tools are responsible for acting as the server for TCP performance measurement and analyzing data collected from the client side.

### Build
#### Dependencies
##### Python3 Dependencies (client & server)
`pip3 install -r requirements.txt`

##### client requirements
- **QT5**: `qmake` is used for Makefiles generation of `roamingd`;
- **GPS**: `gpxlogger`;
- packages listed in carfi_dependencies.txt;
- **systemd**: your system has to support `systemd`.

##### Server requirements
- **Database**: mysql  Ver 14.14 Distrib 5.7.25, for Linux (x86_64) using  EditLine wrapper;
- **systemd**: your system has to support `systemd`.

#### Building Commands
##### Client tools (X-Fi and X-Perf)
1. Change `QMAKE` variable in `./bootstrap.sh` to the location of `qmake` in your system;
2. `./bootstrap.sh`
3. Compilation and installation:
```
cd client_tools 
make
sudo make install
```
4. GPS settings

**WARNING: This step must be excuted manually. And creating backup for original files is highly recommended.**

`gpsdctl@.service` has to be called after the GPS hardware is ready. So, we added a small sleeping period before it. Please use `./client_tools/system-conf/gpsdctl@.service` to replace the original one -- `/lib/systemd/system/gpsdctl@.service`. 

##### Server tools (Uploader server, TCP server for performance measurement)
1. Compilation and installation:
```
cd server_tools
make
sudo make install_tcpserver
sudo make install_analyzer
```

### Usage
#### Change system settings
1. run `config_journald.sh  config_sysctl.sh  enable_bbr_ko.sh`

#### Client tools
1. configure X-Perf for data collection:
    - open `client_tools/carfi/carfi.json`
    - change the interface (wlp4s0) name to your wireless interface
    - change the wpa_conf file to your wpa_conf file (placed in `client_tools/carfi/etc`)
    - open `client_tools/carfi/etc/test_initator.json`
    - change the interface (wlp4s0) name to your wireless interface
    - change the TCP test configurations (CC list, flow number list, TCP server IP) according to your needs
    - open `client_tools/collector/collector_daemon`
    - change the settings of collector
        - DATA_PATH = "/opt/carfi/data" # where to store runtime data
        - TAR_PATH = "/opt/carfi/tar" # where to store archived data
        - LOC_MARKER = "Paris" # location marker (used for naming collected data)
        - DURATION = 300 #secs # length of a single experiment run

2. configure X-Perf for data uploading:
    - open `client_tools/data_uploader/uploader_client_daemon`
    - change the settings of uploader
        - SERVER_IP="132.227.122.22" # uploader server ip
        - SERVER_PORT=9999 # uploader server port
        - INTERFACE="wlxc83a35d1021c" # uploader network interface name (e.g. a cellular dongle)
        - TAR_PATH="/opt/carfi/tar" # where to find archived data
    - configure routing table:
        - you must configure your routing table (via `ip route`) to send all traffic destinated to the uploader server via the uploader interface.

3. run X-Perf
    - Once `make install` is executed successfully, the X-Fi client is registered as a systemd service called `carfi-data-collector.service`. The command `systemctl start carfi-data-collector.service` can be used for starting the client. Also, the service is started automatically when the system is booting or rebooting. If you don't want the autostart feature, you use `systemctl disable carfi-data-collector.service` to disable it.
    - Similarily, you can run `systemctl start carfi-uploader-client.service` to start uploader.

4. check if you are collecting data by going to `DATA_PATH` and `TAR_PATH` above.



#### Server tools
1. run the TCP server for performance measurement
    - open `server_tools/tester/tcp_server_daemon` to change configurations
        - UPLOAD_PORT_BASE=5000 # upload port
        - DOWNLOAD_PORT_BASE=5100 # download port
        - CC_LIST="cubic,bbr" # CCA list. It must be in the same order as the one in `tester_initator.json`
        - INTERFACE=ens3 # the network interface used for TCP performance measurement
    - `systemctl start carfi-tcpserver.service`

2. run the TCP uploader server
    - open `server_tools/data-uploader/tcp_server_daemon` to change configurations
        - UPLOADER_PORT=9999 # uploader server port
        - UPLOADER_RECV_DIR=/opt/carfi/recv_dir # where to recv archived data
        - UPLOADER_TAR_DIR=/opt/carfi/tar_dir # where to store archived data
    - `systemctl start carfi-uploader-server.service`

3. some scripts for data analysis
    - the scripts are located in `server_tools/analyzer`
    - `parser.py`: parsing archived data and saving the results into a database
    - `plotter.py`: reading the data from database and generating plots.

