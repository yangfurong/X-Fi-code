#include <arpa/inet.h>
#include <netinet/tcp.h>
#include <sys/time.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdbool.h>
#include <getopt.h>
#include <stdint.h>
#include <signal.h>
#include <pthread.h>
#include <assert.h>
#include <errno.h>

//#define MQ_INTF

//#define DEBUG
#define BUFSIZE 4096
#define MAX_CC_TYPES 8
#define CC_NAME_LEN 32
#define INTF_NAME_LEN 64

typedef enum {
    UPLOAD = 0,
    DOWNLOAD = 1,
    TYPE_MAX = 2
} server_type_t;

struct {
    uint16_t ul_port_base;
    uint16_t dl_port_base;
    char cc_type[MAX_CC_TYPES][CC_NAME_LEN];
    uint8_t cc_nb;
    char exposed_intf[INTF_NAME_LEN];
} global_args;

typedef struct server_thread_info {
    pthread_t tid;
    uint16_t listen_port;
    server_type_t type;
    uint8_t cc_index;
} svr_thr_info_t;

svr_thr_info_t *svr_thr_infos;

void usage() {
    fprintf(stderr, "Usage: <prog> -u <upload port base> -d <download port base> -c <congestion control algorithm list, seperated by comma, e.g. cubic,bbr,vegas> -i <interface exposed for communication with clients>. All options are mandatory to be provided\n");
    exit(-1);
}

void parse_args(int argc, char **argv) {
    int opt;
    int check = 0;
    while ((opt = getopt(argc, argv, "u:d:c:i:")) != -1) {
        switch(opt) {
            case 'u': global_args.ul_port_base = atoi(optarg); check += 1; break;
            case 'd': global_args.dl_port_base = atoi(optarg); check += 1; break;
            case 'i': strncpy(global_args.exposed_intf, optarg, INTF_NAME_LEN); check += 1; break;
            case 'c': {   char *tok;
                          tok = strtok(optarg, ",");
                          global_args.cc_nb = 0;
                          do {
                              strncpy(global_args.cc_type[global_args.cc_nb++], tok, CC_NAME_LEN);
                          } while ((tok = strtok(NULL, ",")) != NULL);
                          if (global_args.cc_nb == 0) {
                              usage();
                          }
                          check += 1;
                          break;
                      }
            default: usage();
        }
    }
    if (check != 4) {
        usage();
    }
}

void* Data_handle_up(void *sock_fd)
{
    int fd = ((int)sock_fd);
    int i_recvBytes;
    char data_recv[BUFSIZE];
    while(1)
    {
        i_recvBytes = recv(fd, data_recv, BUFSIZE, 0);
        if(i_recvBytes <= 0)
        {
            break;
        }
    }
    close(fd);            //close a file descriptor.
    return NULL;
}

void* Data_handle_down(void *sock_fd)
{
    int fd = ((int)sock_fd);
    int i_sendBytes;
    char data_to_send[BUFSIZE];
    while(1)
    {
        i_sendBytes = send(fd, data_to_send, BUFSIZE, 0);
        if(i_sendBytes == -1)
        {
            break;
        }
    }
    close(fd);            //close a file descriptor.
    return NULL;
}

void* (*data_handler[TYPE_MAX])(void *sockfd) = {Data_handle_up, Data_handle_down};

void* server_start(void *arg) {
    svr_thr_info_t *sv_info = (svr_thr_info_t*)arg;
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        perror("creating socket failed");
        exit(1);
    }
    //set congestion control algorithm
    if (setsockopt(fd, IPPROTO_TCP, TCP_CONGESTION, global_args.cc_type[sv_info->cc_index], strlen(global_args.cc_type[sv_info->cc_index])) < 0) {
        fprintf(stderr, "setsockopt: set tcp congestion control to %s failed\n", global_args.cc_type[sv_info->cc_index]);
        exit(-1);
    }

    int sock_opt = 1;
    assert(setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &sock_opt, sizeof(sock_opt)) >= 0);
    sock_opt = 1;
    assert(setsockopt(fd, SOL_SOCKET, SO_KEEPALIVE, &sock_opt, sizeof(sock_opt)) >= 0);

    struct sockaddr_in sv_addr;
    memset(&sv_addr, 0, sizeof(sv_addr));
    sv_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    sv_addr.sin_family = AF_INET;
    sv_addr.sin_port   = htons(sv_info->listen_port);

    if (bind(fd, (struct sockaddr*)&sv_addr, sizeof(sv_addr)) < 0){
        fprintf(stderr, "binding on port %d is failed (Errno: %d)\n", sv_info->listen_port, errno);
        exit(-1);
    }

    if (listen(fd, 64) < 0) {
        fprintf(stderr, "listening on port %d is failed (Errno: %d)\n", sv_info->listen_port, errno);
        exit(-1);
    }

    fprintf(stdout, "server started on port %d, cc = %s\n", sv_info->listen_port, global_args.cc_type[sv_info->cc_index]);
    fflush(stdout);
    while(1) {
        int cli_fd = accept(fd, NULL, NULL);
        //adjust tc qdisc according to cc algorithm
#ifndef MQ_INTF
        char cmdbuf[256];
        if (strcmp(global_args.cc_type[sv_info->cc_index], "bbr") == 0) {
            snprintf(cmdbuf, 256, "tc qdisc replace dev %s root fq", global_args.exposed_intf);
            system(cmdbuf);
        } else {
            snprintf(cmdbuf, 256, "tc qdisc replace dev %s root pfifo_fast", global_args.exposed_intf);
            system(cmdbuf);
        }
#else
        char cmdbuf[256];
        if (strcmp(global_args.cc_type[sv_info->cc_index], "bbr") == 0) {
            snprintf(cmdbuf, 256, "sysctl -w net.core.default_qdisc=fq; tc qdisc replace dev %s root pfifo_fast; tc qdisc replace dev %s root mq", global_args.exposed_intf, global_args.exposed_intf);
            system(cmdbuf);
        } else {
            snprintf(cmdbuf, 256, "sysctl -w net.core.default_qdisc=pfifo_fast; tc qdisc replace dev %s root pfifo_fast; tc qdisc replace dev %s root mq", global_args.exposed_intf, global_args.exposed_intf);
            system(cmdbuf);
        }
#endif
        //check the congestion control algo, just for debugging
#ifdef DEBUG
        char cc[32] = {0};
        int len = 32;
        assert((getsockopt(cli_fd, IPPROTO_TCP, TCP_CONGESTION, cc, &len)) >= 0);
        printf("cc of flow on port %d: %s\n", sv_info->listen_port, cc);
#endif
        //handle client
        pthread_t tid;
        if ((pthread_create(&tid, NULL, data_handler[sv_info->type], (void*)cli_fd)) != 0) {
            //if something goes wrong, we just ingore it in this time
            fprintf(stderr, "pthread create failed on port %d\n", sv_info->listen_port);
            fflush(stderr);
        } else {
            pthread_detach(tid);
        }
    }
    close(fd);
    return NULL;
}

int main(int argc, char* argv[]) {

    parse_args(argc, argv);
    signal(SIGPIPE, SIG_IGN);

    int svr_thr_infos_len = global_args.cc_nb * TYPE_MAX;
    svr_thr_infos = (svr_thr_info_t*)malloc(sizeof(svr_thr_info_t) * svr_thr_infos_len);
    memset(svr_thr_infos, 0, sizeof(svr_thr_info_t) * svr_thr_infos_len);

    int i, thr_id;
    for (i = 0, thr_id = 0; i < global_args.cc_nb; i++, thr_id += 2) {
        svr_thr_infos[thr_id].listen_port = global_args.ul_port_base + i;
        svr_thr_infos[thr_id].type = UPLOAD;
        svr_thr_infos[thr_id].cc_index = i;

        svr_thr_infos[thr_id+1].listen_port = global_args.dl_port_base + i;
        svr_thr_infos[thr_id+1].type = DOWNLOAD;
        svr_thr_infos[thr_id+1].cc_index = i;

        if (pthread_create(&(svr_thr_infos[thr_id].tid), NULL, server_start, (void*)&svr_thr_infos[thr_id]) != 0) {
            fprintf(stderr, "create server thread on port %d failed\n", svr_thr_infos[thr_id].listen_port);
            exit(-1);
        }

        if (pthread_create(&(svr_thr_infos[thr_id+1].tid), NULL, server_start, (void*)&svr_thr_infos[thr_id+1]) != 0) {
            fprintf(stderr, "create server thread on port %d failed\n", svr_thr_infos[thr_id+1].listen_port);
            exit(-1);
        }
    }

    for (thr_id = 0; thr_id < 2*global_args.cc_nb; thr_id++) {
        pthread_join(svr_thr_infos[thr_id].tid, NULL);
    }

    return 0;
}
