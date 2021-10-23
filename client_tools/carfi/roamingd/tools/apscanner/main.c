#include <errno.h>
#include <net/if.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

#include <netlink/genl/genl.h>
#include <netlink/genl/family.h>
#include <netlink/genl/ctrl.h>
#include <netlink/msg.h>
#include <netlink/attr.h>

#include "iw.h"

int iw_debug = 0;

static int nl80211_init(struct nl80211_state *state)
{
	int err;

	state->nl_sock = nl_socket_alloc();
	if (!state->nl_sock) {
		fprintf(stderr, "Failed to allocate netlink socket\n");
		return -ENOMEM;
	}

	nl_socket_set_buffer_size(state->nl_sock, 8192, 8192);

	if (genl_connect(state->nl_sock)) {
		fprintf(stderr, "Failed to connect to generic netlink\n");
		err = -ENOLINK;
		goto out_handle_destroy;
	}

	state->nl80211_id = genl_ctrl_resolve(state->nl_sock, "nl80211");
	if (state->nl80211_id < 0) {
		fprintf(stderr, "nl80211 not found\n");
		err = -ENOENT;
		goto out_handle_destroy;
	}

	return 0;

 out_handle_destroy:
	nl_socket_free(state->nl_sock);
	return err;
}

static void nl80211_cleanup(struct nl80211_state *state)
{
	nl_socket_free(state->nl_sock);
}

static int phy_lookup(char *name)
{
	char buf[200];
	int fd, pos;

	snprintf(buf, sizeof(buf), "/sys/class/ieee80211/%s/index", name);

	fd = open(buf, O_RDONLY);
	if (fd < 0)
		return -1;
	pos = read(fd, buf, sizeof(buf) - 1);
	if (pos < 0) {
		close(fd);
		return -1;
	}
	buf[pos] = '\0';
	close(fd);
	return atoi(buf);
}

static int error_handler(struct sockaddr_nl *nla, struct nlmsgerr *err,
			 void *arg)
{
	int *ret = arg;
	*ret = err->error;
	return NL_STOP;
}

static int finish_handler(struct nl_msg *msg, void *arg)
{
	int *ret = arg;
	*ret = 0;
	return NL_SKIP;
}

static int ack_handler(struct nl_msg *msg, void *arg)
{
	int *ret = arg;
	*ret = 0;
	return NL_STOP;
}

typedef int (*command_handler)(struct nl80211_state *state,
			       struct nl_cb *cb,
			       struct nl_msg *msg,
			       int argc, char **argv,
			       enum id_input id);

static int handle_cmd(struct nl80211_state *state, enum id_input idby,
		      enum nl80211_commands nlcmd, int nlflags,
		      const command_handler handler,
		      int argc, char **argv)
{
	struct nl_cb *cb;
	struct nl_cb *s_cb;
	struct nl_msg *msg;
	signed long long devidx = 0;
	int err;
	char *tmp;
	enum command_identify_by command_idby = CIB_NONE;

	if (argc == 0 && idby != II_NONE)
		return 1;

	switch (idby) {
	case II_PHY_IDX:
		command_idby = CIB_PHY;
		devidx = strtoul(*argv + 4, &tmp, 0);
		if (*tmp != '\0')
			return 1;
		argc--;
		argv++;
		break;
	case II_PHY_NAME:
		command_idby = CIB_PHY;
		devidx = phy_lookup(*argv);
		argc--;
		argv++;
		break;
	case II_NETDEV:
		command_idby = CIB_NETDEV;
		devidx = if_nametoindex(*argv);
		if (devidx == 0)
			devidx = -1;
		argc--;
		argv++;
		break;
	case II_WDEV:
		command_idby = CIB_WDEV;
		devidx = strtoll(*argv, &tmp, 0);
		if (*tmp != '\0')
			return 1;
		argc--;
		argv++;
	default:
		break;
	}

	if (devidx < 0)
		return -errno;

	msg = nlmsg_alloc();
	if (!msg) {
		fprintf(stderr, "Failed to allocate netlink message\n");
		return 2;
	}

	cb = nl_cb_alloc(iw_debug ? NL_CB_DEBUG : NL_CB_DEFAULT);
	s_cb = nl_cb_alloc(iw_debug ? NL_CB_DEBUG : NL_CB_DEFAULT);
	if (!cb || !s_cb) {
		fprintf(stderr, "Failed to allocate netlink callbacks\n");
		err = 2;
		goto out_free_msg;
	}

	genlmsg_put(msg, 0, 0, state->nl80211_id, 0, nlflags, nlcmd, 0);

	switch (command_idby) {
	case CIB_PHY:
		NLA_PUT_U32(msg, NL80211_ATTR_WIPHY, devidx);
		break;
	case CIB_NETDEV:
		NLA_PUT_U32(msg, NL80211_ATTR_IFINDEX, devidx);
		break;
	case CIB_WDEV:
		NLA_PUT_U64(msg, NL80211_ATTR_WDEV, devidx);
		break;
	default:
		break;
	}

	err = handler(state, cb, msg, argc, argv, idby);
	if (err)
		goto out;

	nl_socket_set_cb(state->nl_sock, s_cb);

	err = nl_send_auto_complete(state->nl_sock, msg);
	if (err < 0)
		goto out;

	err = 1;

	nl_cb_err(cb, NL_CB_CUSTOM, error_handler, &err);
	nl_cb_set(cb, NL_CB_FINISH, NL_CB_CUSTOM, finish_handler, &err);
	nl_cb_set(cb, NL_CB_ACK, NL_CB_CUSTOM, ack_handler, &err);

	while (err > 0)
		nl_recvmsgs(state->nl_sock, cb);

 out:
	nl_cb_put(cb);
 out_free_msg:
	nlmsg_free(msg);
	return err;
 nla_put_failure:
	fprintf(stderr, "Building message failed\n");
	return 2;
}

static int perform_scan(struct nl80211_state *state, enum id_input id,
			int argc, char **argv)
{
	int err = handle_cmd(state, id, NL80211_CMD_TRIGGER_SCAN, 0,
			     handle_scan, argc, argv);
	if (err)
		return err;

	/*
	 * This code has a bug, which requires creating a separate
	 * nl80211 socket to fix:
	 * It is possible for a NL80211_CMD_NEW_SCAN_RESULTS or
	 * NL80211_CMD_SCAN_ABORTED message to be sent by the kernel
	 * before (!) we listen to it, because we only start listening
	 * after we send our scan request.
	 *
	 * Doing it the other way around has a race condition as well,
	 * if you first open the events socket you may get a notification
	 * for a previous scan.
	 *
	 * The only proper way to fix this would be to listen to events
	 * before sending the command, and for the kernel to send the
	 * scan request along with the event, so that you can match up
	 * whether the scan you requested was finished or aborted (this
	 * may result in processing a scan that another application
	 * requested, but that doesn't seem to be a problem).
	 *
	 * Alas, the kernel doesn't do that (yet).
	 */

	static const __u32 cmds[] = {
		NL80211_CMD_NEW_SCAN_RESULTS,
		NL80211_CMD_SCAN_ABORTED,
	};
	if (listen_events(state, ARRAY_SIZE(cmds), cmds) == NL80211_CMD_SCAN_ABORTED) {
		printf("Scan aborted!\n");
		return 0;
	}

	return handle_cmd(state, id, NL80211_CMD_GET_SCAN, NLM_F_DUMP,
			  handle_scan_dump, argc, argv);
}

int main(int argc, char **argv)
{
	struct nl80211_state nlstate;
	int err;
	enum id_input idby = II_NONE;

	/* strip off self */
	argc--;
	argv++;

	if (argc == 0) {
		fprintf(stderr, "Empty command line\n");
		return 1;
	}

	if (strcmp(*argv, "--debug") == 0) {
		iw_debug = 1;
		argc--;
		argv++;
	}

	err = nl80211_init(&nlstate);
	if (err)
		return err;

	if (strcmp(*argv, "dev") == 0 && argc > 1) {
		argc--;
		argv++;
		idby = II_NETDEV;
	} else if (strncmp(*argv, "phy", 3) == 0 && argc > 1) {
		if (strlen(*argv) == 3) {
			argc--;
			argv++;
			idby = II_PHY_NAME;
		} else if (*(*argv + 3) == '#')
			idby = II_PHY_IDX;
	} else if (strcmp(*argv, "wdev") == 0 && argc > 1) {
		argc--;
		argv++;
		idby = II_WDEV;
	}

	if (idby == II_NONE) {
		if (if_nametoindex(argv[0]) != 0)
			idby = II_NETDEV;
		else if (phy_lookup(argv[0]) >= 0)
			idby = II_PHY_NAME;
	}

	err = perform_scan(&nlstate, idby, argc, argv);

	if (err == 1) {
		fprintf(stderr, "Invalid command line arguments\n");
	} else if (err < 0)
		fprintf(stderr, "Command failed: %s (%d)\n", strerror(-err), err);

	nl80211_cleanup(&nlstate);

	return err;
}
