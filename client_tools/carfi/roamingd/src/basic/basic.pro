TEMPLATE = lib
TARGET = roamingd-basic

CONFIG += staticlib thread
CONFIG -= qt

include(../defines.pri)

HEADERS = \
	alloc-util.h \
	architecture.h \
	async.h \
	conf-files.h \
	conf-parser.h \
	def.h \
	device-nodes.h \
	dirent-util.h \
	dns-domain.h \
	env-util.h \
	escape.h \
	exit-status.h \
	extract-word.h \
	fd-util.h \
	fileio.h \
	firewall-util.h \
	formats-util.h \
	fs-util.h \
	gunicode.h \
	hash-funcs.h \
	hashmap.h \
	hexdecoct.h \
	hostname-util.h \
	in-addr-util.h \
	ioprio.h \
	io-util.h \
	list.h \
	log.h \
	macro.h \
	mempool.h \
	missing.h \
	missing_syscall.h \
	mkdir.h \
	ordered-set.h \
	parse-util.h \
	path-util.h \
	prioq.h \
	proc-cmdline.h \
	process-util.h \
	random-util.h \
	refcnt.h \
	resolve-util.h \
	_sd-common.h \
	sd-daemon.h \
	sd-event.h \
	sd-id128.h \
	set.h \
	signal-util.h \
	siphash24.h \
	socket-util.h \
	sparse-endian.h \
	stat-util.h \
	stdio-util.h \
	string-table.h \
	string-util.h \
	strv.h \
	syslog-util.h \
	terminal-util.h \
	time-util.h \
	umask-util.h \
	unaligned.h \
	user-util.h \
	utf8.h \
	util.h

SOURCES = \
	alloc-util.c \
	architecture.c \
	async.c \
	conf-files.c \
	conf-parser.c \
	device-nodes.c \
	dirent-util.c \
	dns-domain.c \
	env-util.c \
	escape.c \
	exit-status.c \
	extract-word.c \
	fd-util.c \
	fileio.c \
	fs-util.c \
	gunicode.c \
	hash-funcs.c \
	hashmap.c \
	hexdecoct.c \
	hostname-util.c \
	in-addr-util.c \
	io-util.c \
	log.c \
	mempool.c \
	mkdir.c \
	ordered-set.c \
	parse-util.c \
	path-util.c \
	prioq.c \
	proc-cmdline.c \
	process-util.c \
	random-util.c \
	resolve-util.c \
	sd-daemon.c \
	sd-event.c \
	sd-id128.c \
	signal-util.c \
	siphash24.c \
	socket-util.c \
	stat-util.c \
	string-table.c \
	string-util.c \
	strv.c \
	syslog-util.c \
	terminal-util.c \
	time-util.c \
	user-util.c \
	utf8.c \
	util.c
