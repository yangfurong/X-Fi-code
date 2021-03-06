#pragma once

/***
  This file is part of systemd.

  Copyright 2013 Tom Gundersen <teg@jklm.no>

  systemd is free software; you can redistribute it and/or modify it
  under the terms of the GNU Lesser General Public License as published by
  the Free Software Foundation; either version 2.1 of the License, or
  (at your option) any later version.

  systemd is distributed in the hope that it will be useful, but
  WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
  Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public License
  along with systemd; If not, see <http://www.gnu.org/licenses/>.
***/

#include <endian.h>

#include "sd-dhcp-client.h"
#include "sd-dhcp-server.h"
#include "sd-dhcp6-client.h"
#include "sd-ndisc.h"

typedef struct Link Link;

typedef enum LinkState {
        LINK_STATE_PENDING,
        LINK_STATE_ENSLAVING,
        LINK_STATE_SETTING_ADDRESSES,
        LINK_STATE_SETTING_ROUTES,
        LINK_STATE_CONFIGURED,
        LINK_STATE_UNMANAGED,
        LINK_STATE_FAILED,
        LINK_STATE_LINGER,
        _LINK_STATE_MAX,
        _LINK_STATE_INVALID = -1
} LinkState;

typedef enum LinkOperationalState {
        LINK_OPERSTATE_OFF,
        LINK_OPERSTATE_NO_CARRIER,
        LINK_OPERSTATE_DORMANT,
        LINK_OPERSTATE_CARRIER,
        LINK_OPERSTATE_DEGRADED,
        LINK_OPERSTATE_ROUTABLE,
        _LINK_OPERSTATE_MAX,
        _LINK_OPERSTATE_INVALID = -1
} LinkOperationalState;

#include "roamingd-address.h"
#include "roamingd-network.h"
#include "roamingd-manager.h"

struct Link {
        Manager *manager;

        int n_ref;

        int ifindex;
        char *ifname;
        unsigned short iftype;
        char *state_file;
        struct ether_addr mac;
        struct in6_addr ipv6ll_address;
        uint32_t mtu;

        unsigned flags;
        uint8_t kernel_operstate;

        Network *network;

        LinkState state;
        LinkOperationalState operstate;

        unsigned link_messages;
        unsigned enslaving;

        Set *addresses;
        Set *addresses_foreign;
        Set *routes;
        Set *routes_foreign;

        sd_dhcp_client *dhcp_client;
        sd_dhcp_lease *dhcp_lease;
        char *lease_file;
        uint16_t original_mtu;
        unsigned dhcp4_messages;
        bool dhcp4_configured;
        bool dhcp6_configured;
        unsigned ndisc_messages;
        bool ndisc_configured;

        bool ipv4ll_address:1;
        bool ipv4ll_route:1;

        bool static_configured;

        LIST_HEAD(Address, pool_addresses);

        sd_dhcp_server *dhcp_server;

        sd_ndisc *ndisc_router_discovery;
        sd_dhcp6_client *dhcp6_client;
        bool rtnl_extended_attrs;

        Hashmap *bound_by_links;
        Hashmap *bound_to_links;
};

Link *link_unref(Link *link);
Link *link_ref(Link *link);
int link_get(Manager *m, int ifindex, Link **ret);
int link_add(Manager *manager, sd_netlink_message *message, Link **ret);
void link_drop(Link *link);

int link_address_remove_handler(sd_netlink *rtnl, sd_netlink_message *m, void *userdata);
int link_route_remove_handler(sd_netlink *rtnl, sd_netlink_message *m, void *userdata);

void link_enter_failed(Link *link);

void link_check_ready(Link *link);

void link_update_operstate(Link *link);
int link_update(Link *link, sd_netlink_message *message);

void link_dirty(Link *link);
void link_clean(Link *link);
int link_save(Link *link);

int link_carrier_reset(Link *link);
bool link_has_carrier(Link *link);

int link_ipv6ll_gained(Link *link, const struct in6_addr *address);

int link_set_mtu(Link *link, uint32_t mtu);
int link_set_hostname(Link *link, const char *hostname);
int link_set_timezone(Link *link, const char *timezone);

int ipv4ll_configure(Link *link);
int dhcp4_configure(Link *link);
int dhcp6_configure(Link *link);
int dhcp6_request_address(Link *link);
int ndisc_configure(Link *link);

const char* link_state_to_string(LinkState s) _const_;
LinkState link_state_from_string(const char *s) _pure_;

const char* link_operstate_to_string(LinkOperationalState s) _const_;
LinkOperationalState link_operstate_from_string(const char *s) _pure_;

int link_send_changed(Link *link, const char *property, ...) _sentinel_;

DEFINE_TRIVIAL_CLEANUP_FUNC(Link*, link_unref);
#define _cleanup_link_unref_ _cleanup_(link_unrefp)

/* Macros which append INTERFACE= to the message */

#define log_link_full(link, level, error, ...)                          \
        ({                                                              \
                Link *_l = (link);                                      \
                _l ? log_object_internal(level, error, __FILE__, __LINE__, __func__, "INTERFACE=", _l->ifname, ##__VA_ARGS__) : \
                        log_internal(level, error, __FILE__, __LINE__, __func__, ##__VA_ARGS__); \
        })                                                              \

#define log_link_debug(link, ...)   log_link_full(link, LOG_DEBUG, 0, ##__VA_ARGS__)
#define log_link_info(link, ...)    log_link_full(link, LOG_INFO, 0, ##__VA_ARGS__)
#define log_link_notice(link, ...)  log_link_full(link, LOG_NOTICE, 0, ##__VA_ARGS__)
#define log_link_warning(link, ...) log_link_full(link, LOG_WARNING, 0, ##__VA_ARGS__)
#define log_link_error(link, ...)   log_link_full(link, LOG_ERR, 0, ##__VA_ARGS__)

#define log_link_debug_errno(link, error, ...)   log_link_full(link, LOG_DEBUG, error, ##__VA_ARGS__)
#define log_link_info_errno(link, error, ...)    log_link_full(link, LOG_INFO, error, ##__VA_ARGS__)
#define log_link_notice_errno(link, error, ...)  log_link_full(link, LOG_NOTICE, error, ##__VA_ARGS__)
#define log_link_warning_errno(link, error, ...) log_link_full(link, LOG_WARNING, error, ##__VA_ARGS__)
#define log_link_error_errno(link, error, ...)   log_link_full(link, LOG_ERR, error, ##__VA_ARGS__)

#define LOG_LINK_MESSAGE(link, fmt, ...) "MESSAGE=%s: " fmt, (link)->ifname, ##__VA_ARGS__
#define LOG_LINK_INTERFACE(link) "INTERFACE=%s", (link)->ifname

#define ADDRESS_FMT_VAL(address)                   \
        be32toh((address).s_addr) >> 24,           \
        (be32toh((address).s_addr) >> 16) & 0xFFu, \
        (be32toh((address).s_addr) >> 8) & 0xFFu,  \
        be32toh((address).s_addr) & 0xFFu
