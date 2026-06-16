#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/ip.h>
#include <sys/types.h>
#include <ifaddrs.h>
#include <netinet/in.h>
#include <net/if.h>


#define LISTEN_PORT 5012
#define BUFFER_SIZE 4096

// 获取本机IP
int get_local_ip(char *ip_buffer, size_t buffer_size) {
    struct ifaddrs *ifaddr, *ifa;
    int family;
    if (getifaddrs(&ifaddr) == -1) {
        perror("getifaddrs");
        return -1;
    }

    // 遍历接口列表，寻找第一个IPv4地址
    for (ifa = ifaddr; ifa != NULL; ifa = ifa->ifa_next) {
        if (ifa->ifa_addr == NULL) continue;
        family = ifa->ifa_addr->sa_family;
        
        // 只需要第一个非回环的IPv4地址
        if (family == AF_INET && !(ifa->ifa_flags & IFF_LOOPBACK)) {
            struct sockaddr_in *addr = (struct sockaddr_in *)ifa->ifa_addr;
            inet_ntop(AF_INET, &addr->sin_addr, ip_buffer, buffer_size);
            freeifaddrs(ifaddr);
            return 0;
        }
    }

    freeifaddrs(ifaddr);
    return -1;
}

int main() {
    int sockfd;
    struct sockaddr_in listen_addr, client_addr, forward_addr;
    socklen_t addr_len = sizeof(client_addr);
    unsigned char buffer[BUFFER_SIZE];
    char local_ip[INET_ADDRSTRLEN];

    // 获取本机IP
    if (get_local_ip(local_ip, sizeof(local_ip)) < 0) {
        fprintf(stderr, "Failed to obtain local IP\n");
        exit(EXIT_FAILURE);
    }
    printf("Local IP detected: %s\n", local_ip);

    // 创建UDP套接字
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    // 设置监听地址和端口
    memset(&listen_addr, 0, sizeof(listen_addr));
    listen_addr.sin_family = AF_INET;
    listen_addr.sin_addr.s_addr = inet_addr(local_ip);
    listen_addr.sin_port = htons(LISTEN_PORT);

    // 绑定套接字
    if (bind(sockfd, (struct sockaddr *)&listen_addr, sizeof(listen_addr)) < 0) {
        perror("bind");
        close(sockfd);
        exit(EXIT_FAILURE);
    }

    printf("Listening for UDP packets on %s:%d...\n", local_ip, LISTEN_PORT);

    // 设置固定的转发地址和端口
    memset(&forward_addr, 0, sizeof(forward_addr));
    forward_addr.sin_family = AF_INET;
    forward_addr.sin_addr.s_addr = inet_addr("10.0.14.149");
    forward_addr.sin_port = htons(1235);

    while (1) {
        // 接收数据包
        ssize_t received_size = recvfrom(sockfd, buffer, BUFFER_SIZE, 0, 
                                          (struct sockaddr *)&client_addr, &addr_len);
        if (received_size < 0) {
            perror("recvfrom");
            continue;
        }

        printf("Received packet from %s:%d, forwarding\n",
               inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

        // 直接将数据包发送到指定的目标地址和端口
        if (sendto(sockfd, buffer, received_size, 0, 
                   (struct sockaddr *)&forward_addr, sizeof(forward_addr)) < 0) {
            perror("sendto");
        } else {
            printf("Packet forwarded successfully.\n");
        }
    }

    close(sockfd);
    return 0;
}

