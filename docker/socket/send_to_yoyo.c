#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/ip.h>

#define LISTEN_PORT 1235
#define BUFFER_SIZE 4096

// 将 192.168.x.x 转换为 172.16.x.x
void convert_ip(const char *src_ip, char *dest_ip) {
    if (strncmp(src_ip, "192.168", 7) == 0) {
        snprintf(dest_ip, INET_ADDRSTRLEN, "172.17%s", src_ip + 7);
    } else {
        strncpy(dest_ip, src_ip, INET_ADDRSTRLEN);
    }
}

// 解析 IP 头并打印信息
void print_ip_info(const unsigned char *packet, ssize_t size) {
    struct iphdr *ip_header = (struct iphdr *)packet;

    struct in_addr src_addr, dest_addr;
    src_addr.s_addr = ip_header->saddr;
    dest_addr.s_addr = ip_header->daddr;

    printf("Source IP: %s\n", inet_ntoa(src_addr));
    printf("Destination IP: %s\n", inet_ntoa(dest_addr));

    printf("Payload Size: %ld bytes\n", size - (ip_header->ihl * 4));
}

int main() {
    int sockfd;
    struct sockaddr_in listen_addr, client_addr;
    socklen_t addr_len = sizeof(client_addr);
    unsigned char buffer[BUFFER_SIZE];
    char dest_ip[INET_ADDRSTRLEN];
    char converted_ip[INET_ADDRSTRLEN];

    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    memset(&listen_addr, 0, sizeof(listen_addr));
    listen_addr.sin_family = AF_INET;
    listen_addr.sin_addr.s_addr = inet_addr("0.0.0.0");
    listen_addr.sin_port = htons(LISTEN_PORT);

    if (bind(sockfd, (struct sockaddr *)&listen_addr, sizeof(listen_addr)) < 0) {
        perror("bind");
        close(sockfd);
        exit(EXIT_FAILURE);
    }

    printf("Listening for UDP packets on %s:%d...\n", "0.0.0.0", LISTEN_PORT);

    while (1) {
        ssize_t received_size = recvfrom(sockfd, buffer, BUFFER_SIZE, 0, 
                                          (struct sockaddr *)&client_addr, &addr_len);
        if (received_size < 0) {
            perror("recvfrom");
            continue;
        }

        print_ip_info(buffer, received_size);

        struct iphdr *ip_header = (struct iphdr *)buffer;
        struct in_addr dest_addr;
        dest_addr.s_addr = ip_header->daddr;
        strcpy(dest_ip, inet_ntoa(dest_addr));

        printf("Received packet from %s:%d, destination IP: %s\n",
               inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port), dest_ip);

        // 转换目标 IP 地址
        convert_ip(dest_ip, converted_ip);

        struct sockaddr_in forward_addr;
        memset(&forward_addr, 0, sizeof(forward_addr));
        forward_addr.sin_family = AF_INET;
        forward_addr.sin_addr.s_addr = inet_addr(converted_ip);
        forward_addr.sin_port = htons(6789);

        sendto(sockfd, buffer, received_size, 0, 
               (struct sockaddr *)&forward_addr, sizeof(forward_addr));
        printf("Forwarded packet to %s\n", converted_ip);
    }

    close(sockfd);
    return 0;
}

