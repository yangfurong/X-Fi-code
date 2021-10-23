#pragma once

#include <endian.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include <netlink/netlink.h>
#include <netlink/genl/genl.h>
#include <netlink/genl/family.h>
#include <netlink/genl/ctrl.h>

#include "nl80211.h"
#include "ieee80211.h"

#define ETH_ALEN 6

struct nl80211_state {
	struct nl_sock *nl_sock;
	int nl80211_id;
};

enum command_identify_by {
	CIB_NONE,
	CIB_PHY,
	CIB_NETDEV,
	CIB_WDEV,
};

enum id_input {
	II_NONE,
	II_NETDEV,
	II_PHY_NAME,
	II_PHY_IDX,
	II_WDEV,
};

#define ARRAY_SIZE(ar) (sizeof(ar)/sizeof(ar[0]))
#define BIT(x) (1ULL<<(x))
#define DIV_ROUND_UP(x, y) (((x) + (y - 1)) / (y))

extern int iw_debug;

struct print_event_args {
	struct timeval ts; /* internal */
	bool have_ts; /* must be set false */
	bool frame, time, reltime;
};

__u32 listen_events(struct nl80211_state *state,
		    const int n_waits, const __u32 *waits);
int __prepare_listen_events(struct nl80211_state *state);
__u32 __do_listen_events(struct nl80211_state *state,
			 const int n_waits, const __u32 *waits,
			 struct print_event_args *args);
int print_events(struct nl80211_state *state,
		 struct nl_cb *cb, struct nl_msg *msg,
		 int argc, char **argv, enum id_input id);

int mac_addr_a2n(unsigned char *mac_addr, char *arg);
void mac_addr_n2a(char *mac_addr, unsigned char *arg);
int parse_hex_mask(char *hexmask, unsigned char **result, size_t *result_len,
		   unsigned char **mask);
unsigned char *parse_hex(char *hex, size_t *outlen);

int parse_keys(struct nl_msg *msg, char **argv, int argc);

void print_ht_mcs(const __u8 *mcs);
void print_ampdu_length(__u8 exponent);
void print_ampdu_spacing(__u8 spacing);
void print_ht_capability(__u16 cap);
void print_vht_info(__u32 capa, const __u8 *mcs);

char *channel_width_name(enum nl80211_chan_width width);
const char *iftype_name(enum nl80211_iftype iftype);
const char *command_name(enum nl80211_commands cmd);
int ieee80211_channel_to_frequency(int chan, enum nl80211_band band);
int ieee80211_frequency_to_channel(int freq);

void print_ssid_escaped(const uint8_t len, const uint8_t *data);

int nl_get_multicast_id(struct nl_sock *sock, const char *family, const char *group);

char *reg_initiator_to_string(__u8 initiator);

const char *get_reason_str(uint16_t reason);
const char *get_status_str(uint16_t status);

enum print_ie_type {
	PRINT_SCAN,
	PRINT_LINK,
};

void print_ies(unsigned char *ie, int ielen, bool unknown,
	       enum print_ie_type ptype);

void parse_bitrate(struct nlattr *bitrate_attr, char *buf, int buflen);
void iw_hexdump(const char *prefix, const __u8 *data, size_t len);

int parse_sched_scan(struct nl_msg *msg, int *argc, char ***argv);

int handle_scan(struct nl80211_state *state,
		struct nl_cb *cb, struct nl_msg *msg,
		int argc, char **argv, enum id_input id);

int handle_scan_dump(struct nl80211_state *state,
		     struct nl_cb *cb, struct nl_msg *msg,
		     int argc, char **argv, enum id_input id);
