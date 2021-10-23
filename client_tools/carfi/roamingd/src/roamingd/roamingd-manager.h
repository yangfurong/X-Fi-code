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

#include <arpa/inet.h>

#include "sd-event.h"
#include "sd-netlink.h"

#include "hashmap.h"
#include "list.h"

typedef struct Manager Manager;

#include "roamingd-address-pool.h"
#include "roamingd-link.h"
#include "roamingd-network.h"
#include "roamingd-util.h"
#include "dhcp-identifier.h"

struct Manager {
        sd_netlink *rtnl;
        sd_event *event;

        bool enumerating:1;
        bool dirty:1;

        Set *dirty_links;

        char *state_file;
        LinkOperationalState operational_state;

        Hashmap *links;
        Hashmap *netdevs;
        Hashmap *networks_by_name;
        LIST_HEAD(Network, networks);
        LIST_HEAD(AddressPool, address_pools);

        DHCPDUIDType dhcp_duid_type;
        size_t dhcp_duid_len;
        struct duid dhcp_duid;
};

/* Manager */

int manager_new(Manager **ret);
void manager_free(Manager *m);

int manager_connect_bus(Manager *m);
int manager_run(Manager *m);

int manager_load_config(Manager *m);
bool manager_should_reload(Manager *m);

int manager_rtnl_enumerate_links(Manager *m);
int manager_rtnl_enumerate_addresses(Manager *m);
int manager_rtnl_enumerate_routes(Manager *m);

int manager_rtnl_process_address(sd_netlink *nl, sd_netlink_message *message, void *userdata);
int manager_rtnl_process_route(sd_netlink *nl, sd_netlink_message *message, void *userdata);

int manager_send_changed(Manager *m, const char *property, ...) _sentinel_;
void manager_dirty(Manager *m);

int manager_address_pool_acquire(Manager *m, int family, unsigned prefixlen, union in_addr_union *found);

Link* manager_find_uplink(Manager *m, Link *exclude);

DEFINE_TRIVIAL_CLEANUP_FUNC(Manager*, manager_free);
#define _cleanup_manager_free_ _cleanup_(manager_freep)
