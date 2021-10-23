#include <arpa/inet.h>
#include <netinet/tcp.h>
#include <sys/time.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>
#include <stdbool.h>
#include <getopt.h>
#include <stdint.h>
#include <signal.h>
#include <pthread.h>
#include <assert.h>

#define BUFSIZE 4096

typedef enum {
    UPLOAD = 0,
    DOWNLOAD = 1,
} client_type;

struct {
    struct in_addr server_ip;
    uint16_t server_port;
    client_type type;
    char cc_type[32];
    char data_dir[256];
    char intf[128];
    int concurrency;
} global_args;

typedef struct cli_thread_info_s{
    uint64_t total_bytes;
    struct timeval start;
    int fd;
    struct sockaddr_in host_addr;
    int cli_id;
} cli_thread_info_t;

cli_thread_info_t *cli_thr_infos;

void usage() {
    fprintf(stderr, "Usage: <prog> -s <server_ip> -p <server_port> -t <type> (0-UPLOAD, 1-DOWNLOAD) -c <congestion control> (e.g. \"cubic\") -d <log_dir> -i <interface>\n");
    exit(-1);
}

void parse_args(int argc, char **argv) {
    int opt;
    while ((opt = getopt(argc, argv, "s:p:t:c:d:n:i:")) != -1) {
        switch(opt) {
            case 'n': global_args.concurrency = atoi(optarg); break;
            case 's': assert(inet_aton(optarg, &global_args.server_ip) >= 0); break;
            case 'p': global_args.server_port = atoi(optarg); break;
            case 't': global_args.type = atoi(optarg); break;
            case 'd': strncpy(global_args.data_dir, optarg, sizeof(global_args.data_dir)); 
                      int i = strlen(global_args.data_dir);
                      while (global_args.data_dir[i-1] == '/') {
                          global_args.data_dir[i-1] = 0;
                          i--;
                      }
                      break;
            case 'c': strncpy(global_args.cc_type, optarg, sizeof(global_args.cc_type)); break;
            case 'i': strncpy(global_args.intf, optarg, sizeof(global_args.intf)); break;
            default: usage();
        }
    }
}

void* client_start(void *arg) {

    cli_thread_info_t *cli_info = (cli_thread_info_t*)arg;

    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        perror("creating socket failed");
        exit(1);
    }

    //set bind device
    //if (setsockopt(fd, SOL_SOCKET, SO_BINDTODEVICE, global_args.intf, strlen(global_args.intf)+1) < 0) {
    //    fprintf(stderr, "setsockopt: bind to device %s failed\n", global_args.intf);
    //    exit(-1);
    //}

    //set congestion control algorithm
    if (setsockopt(fd, IPPROTO_TCP, TCP_CONGESTION, global_args.cc_type, strlen(global_args.cc_type)) < 0) {
        fprintf(stderr, "setsockopt: set tcp congestion control to %s failed\n", global_args.cc_type);
        exit(-1);
    }

    int sock_opt = 1;
    //set tcp keepalive
    if (setsockopt(fd, SOL_SOCKET, SO_KEEPALIVE, &sock_opt, sizeof(sock_opt)) < 0) {
        fprintf(stderr, "setsockopt: set tcp keepalive failed\n");
        exit(-1);
    }

    struct sockaddr_in other;
    memcpy((void*)&other.sin_addr, (void*)&global_args.server_ip, sizeof(global_args.server_ip));
    other.sin_family = AF_INET;
    other.sin_port   = htons(global_args.server_port);

    gettimeofday(&cli_info->start, NULL);
    cli_info->fd = fd;
    cli_info->total_bytes = 0;

    if (connect(fd, (struct sockaddr*)&other, sizeof(other)) != 0) {
        perror("connect");
        exit(1);
    }

    int addr_size = sizeof(cli_info->host_addr);
    if (getsockname(fd, (struct sockaddr*)&cli_info->host_addr, &addr_size) < 0) {
        perror("getsockname failed");
        exit(-1);
    }

    char buf[BUFSIZE];
    int ret;
    fprintf(stdout, "client %d started!\n", cli_info->cli_id);
    while(1) {
        if (global_args.type == UPLOAD) {
            ret = send(cli_info->fd, buf, BUFSIZE, 0);
            //printf("cli_id %d upload %d\n", cli_info->cli_id, ret);
            if (ret < 0)
                break;
        } else {
            ret = recv(cli_info->fd, buf, BUFSIZE, 0);
            //printf("cli_id %d download %d\n", cli_info->cli_id, ret);
            if (ret <= 0) 
                break;
        }
        cli_info->total_bytes += ret;
    }
    fprintf(stdout, "client %d stopped!\n", cli_info->cli_id);
    //It is possible to double-close a socket fd. But it doesn't matter.
    //TODO: find a safer way to fix it.
    close(cli_info->fd);
    return NULL;
}
    

void sig_handler(int sig) {
    fprintf(stdout, "received INT/TERM signal. This program will close soon.\n");
    //store everything
    uint64_t sum_bytes = 0;
    int i;
    for (i = 0; i < global_args.concurrency; i++) {
        close(cli_thr_infos[i].fd);
    }
    //record current time
    struct timeval *tv_start = NULL;
    struct timeval tv_end;
    gettimeofday(&tv_end, NULL);

    //choose the earliest time as the start time
    for (i = 0; i < global_args.concurrency; i++) {
        sum_bytes += cli_thr_infos[i].total_bytes;
        //don't save information if there are connections unestablished
        if ((cli_thr_infos[i].start.tv_sec == 0 && cli_thr_infos[i].start.tv_usec == 0) ||
            (cli_thr_infos[i].host_addr.sin_addr.s_addr == 0)) {
            fprintf(stderr, "connection %d's thread was not even started!\n", i);
            free(cli_thr_infos);
            exit(-1);
        }
        if (tv_start == NULL) {
            tv_start = &cli_thr_infos[i].start;
        } else {
            if (cli_thr_infos[i].start.tv_sec < tv_start->tv_sec || 
                (cli_thr_infos[i].start.tv_sec == tv_start->tv_sec) && 
                (cli_thr_infos[i].start.tv_usec < tv_start->tv_usec)) {
                tv_start = &cli_thr_infos[i].start;
            }
        }
    }
    
    char log_file[512];
    snprintf(log_file, 512, "%s/tcp_tester.profile", global_args.data_dir);
    printf("%s\n", log_file);
    FILE *fp = fopen(log_file, "w");
    assert(fp != NULL);
    fprintf(fp, "%d.%06d\n", tv_start->tv_sec, tv_start->tv_usec);
    fprintf(fp, "%d.%06d\n", tv_end.tv_sec, tv_end.tv_usec);
    fprintf(fp, "%s\n", global_args.type == UPLOAD ? "upload" : "download");
    fprintf(fp, "%s\n", global_args.cc_type);
    fprintf(fp, "%llu\n", (unsigned long long)sum_bytes);
    fprintf(fp, "%d\n", global_args.concurrency);


    for (i = 0; i < global_args.concurrency; i++) {
        fprintf(fp, "%s %d ", inet_ntoa(cli_thr_infos[i].host_addr.sin_addr), ntohs(cli_thr_infos[i].host_addr.sin_port));
        fprintf(fp, "%s %d\n", inet_ntoa(global_args.server_ip), global_args.server_port);
    }
    fflush(fp);
    fclose(fp);
    free(cli_thr_infos);
    fprintf(stdout, "The program ended");
    exit(0);
}


int main(int argc,const char* argv[]) {

    parse_args(argc, argv);

    fprintf(stdout, "%s -s %s -p %d -t %d -c %s -n %d\n", argv[0], inet_ntoa(global_args.server_ip), global_args.server_port, (int)(global_args.type), global_args.cc_type, global_args.concurrency);

    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);
    signal(SIGPIPE, SIG_IGN);

    cli_thr_infos = (cli_thread_info_t*)malloc(sizeof(cli_thread_info_t) * global_args.concurrency);
    memset(cli_thr_infos, 0, sizeof(cli_thread_info_t) * global_args.concurrency);

    int i;
    for (i = 0; i < global_args.concurrency; i++) {
        cli_thr_infos[i].cli_id = i;
        pthread_t tid;
        if(pthread_create(&tid, NULL, client_start, (void*)&cli_thr_infos[i]) < 0) {
            perror("create pthread failed.");
            exit(-1);
        }
        pthread_detach(tid);
    }
    
    uint64_t last_sum = 0, sum_bytes;
    while(1) {
        for (i = 0, sum_bytes = 0; i < global_args.concurrency; i++) {
            sum_bytes += cli_thr_infos[i].total_bytes;
        }
        fprintf(stdout, "goodput: %.4lf Mbps\n", (sum_bytes - last_sum) * 8.0 / 1e6);
        last_sum = sum_bytes;
        sleep(1);
    }
    return 0;
}
