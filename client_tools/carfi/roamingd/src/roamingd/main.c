#include "roamingd-manager.h"
#include "roamingd-network.h"
#include "log.h"

int main(int argc, char *argv[])
{
    Manager *m = NULL;
    int i, r;

    log_set_max_level(LOG_DEBUG);
    log_set_target(LOG_TARGET_CONSOLE);
    log_parse_environment();
    log_open();

    if (argc <= 1) {
        log_error("No interface specified");
        return EXIT_FAILURE;
    }

    r = manager_new(&m);
    if (r < 0) {
        log_error_errno(r, "Could not create manager: %m");
        goto out;
    }

    for (i = 1; i < argc; ++i) {
        r = network_add_interface(m, argv[i]);
        if (r < 0) {
            log_error_errno(r, "Could not create configuration for interface %s: %m", argv[i]);
            goto out;
        }
    }

    r = manager_rtnl_enumerate_links(m);
    if (r < 0) {
        log_error_errno(r, "Could not enumerate links: %m");
        goto out;
    }

    r = manager_rtnl_enumerate_addresses(m);
    if (r < 0) {
        log_error_errno(r, "Could not enumerate addresses: %m");
        goto out;
    }

    r = manager_rtnl_enumerate_routes(m);
    if (r < 0) {
        log_error_errno(r, "Could not enumerate routes: %m");
        goto out;
    }

    log_info("Enumeration completed");

    r = manager_run(m);
    if (r < 0) {
        log_error_errno(r, "Event loop failed: %m");
        goto out;
    }

out:
    manager_free(m);

    return r < 0 ? EXIT_FAILURE : EXIT_SUCCESS;
}
