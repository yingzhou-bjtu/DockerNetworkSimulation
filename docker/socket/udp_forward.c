#include <stdio.h> // 标准输入输出库，用于 printf、perror 等
#include <stdlib.h> // 标准库，用于内存分配、退出程序等
#include <string.h> // 字符串操作函数
#include <unistd.h> // POSIX API，用于 close、read 等
#include <arpa/inet.h> // 提供网络操作相关的定义
#include <netinet/ip.h> // 提供 IP 头部的结构定义
#include <libgen.h> // 提供 dirname 函数
#include "cJSON.h" // JSON 解析库

#define BUFFER_SIZE 4096 // UDP 数据包接收缓冲区大小
#define DEFAULT_JSON_FILE "forward_targets.json" // 默认的 JSON 文件路径

// 定义结构体，存储转发规则中的源 IP 和目标 IP
typedef struct {
    char source_ip[INET_ADDRSTRLEN];
    char destination_ip[INET_ADDRSTRLEN];
} ForwardTarget;

ForwardTarget *forward_targets = NULL; // 动态分配的转发规则数组
int num_targets = 0; // 转发规则的数量

// 加载 JSON 文件中的转发规则
void load_forward_targets(const char *filename) {
    FILE *file = fopen(filename, "r"); // 打开 JSON 文件
    if (!file) {
        perror("无法打开 JSON 文件");
        exit(EXIT_FAILURE);
    }

    fseek(file, 0, SEEK_END); // 移动到文件末尾
    long file_size = ftell(file); // 获取文件大小
    fseek(file, 0, SEEK_SET); // 返回到文件开头

    char *data = malloc(file_size + 1); // 分配内存存储文件内容
    fread(data, 1, file_size, file); // 读取文件内容
    fclose(file);
    data[file_size] = '\0'; // 添加字符串结束符

    // 解析 JSON 数据
    cJSON *json = cJSON_Parse(data);
    if (!json) {
        fprintf(stderr, "JSON 解析错误: %s\n", cJSON_GetErrorPtr());
        free(data);
        exit(EXIT_FAILURE);
    }

    // 获取转发规则数组
    cJSON *targets = cJSON_GetObjectItemCaseSensitive(json, "forward_targets");
    num_targets = cJSON_GetArraySize(targets); // 获取规则数量
    forward_targets = malloc(num_targets * sizeof(ForwardTarget)); // 分配内存

    for (int i = 0; i < num_targets; i++) {
        cJSON *item = cJSON_GetArrayItem(targets, i); // 获取单个规则
        const char *source_ip = cJSON_GetObjectItem(item, "source")->valuestring;
        const char *destination_ip = cJSON_GetObjectItem(item, "destination")->valuestring;
        strncpy(forward_targets[i].source_ip, source_ip, INET_ADDRSTRLEN);
        strncpy(forward_targets[i].destination_ip, destination_ip, INET_ADDRSTRLEN);
    }

    cJSON_Delete(json); // 释放 JSON 对象
    free(data); // 释放数据缓冲区
}

// 解析并打印 IP 头部信息
void print_ip_info(const unsigned char *packet, ssize_t size) {
    struct iphdr *ip_header = (struct iphdr *)packet; // 将数据包视为 IP 头部结构

    // 打印 IP 头部信息
    printf("IP Header Information:\n");
    printf("Version: %d\n", ip_header->version);
    printf("Header Length: %d bytes\n", ip_header->ihl * 4);
    printf("Type of Service: %d\n", ip_header->tos);
    printf("Total Length: %d\n", ntohs(ip_header->tot_len));
    printf("Identification: %d\n", ntohs(ip_header->id));
    printf("Fragment Offset: %d\n", ntohs(ip_header->frag_off));
    printf("Time to Live: %d\n", ip_header->ttl);
    printf("Protocol: %d\n", ip_header->protocol);
    printf("Header Checksum: %d\n", ntohs(ip_header->check));

    struct in_addr src_addr, dest_addr;
    src_addr.s_addr = ip_header->saddr; // 源 IP 地址
    dest_addr.s_addr = ip_header->daddr; // 目标 IP 地址

    printf("Source IP: %s\n", inet_ntoa(src_addr));
    printf("Destination IP: %s\n", inet_ntoa(dest_addr));
    printf("Payload Size: %ld bytes\n", size - (ip_header->ihl * 4)); // 计算有效负载大小
}

int main(int argc, char *argv[]) {
    if (argc < 4 || argc > 5) { // 修改为支持可选的 JSON 文件路径
        fprintf(stderr, "Usage: %s <listen_port> <forward_port> <flag> [json_file_path]\n", argv[0]);
        exit(EXIT_FAILURE);
    }

    int listen_port = atoi(argv[1]); // 监听端口
    int forward_port = atoi(argv[2]); // 转发端口
    int flag = atoi(argv[3]); // 转发模式：0 为源 IP 匹配，1 为目标 IP 匹配
    
    // 动态获取默认 JSON 文件路径
    char default_json_path[512];
    strncpy(default_json_path, argv[0], sizeof(default_json_path) - 1); // 获取可执行文件路径
    default_json_path[sizeof(default_json_path) - 1] = '\0'; // 确保字符串以空字符结尾
    dirname(default_json_path); // 提取可执行文件所在目录
    strncat(default_json_path, "/forward_targets.json", sizeof(default_json_path) - strlen(default_json_path) - 1);

    // 根据参数选择 JSON 文件路径
    const char *json_file_path = (argc == 5) ? argv[4] : default_json_path;

    load_forward_targets(json_file_path); // 使用指定的 JSON 文件加载转发规则

    int sockfd;
    struct sockaddr_in listen_addr, client_addr;
    socklen_t addr_len = sizeof(client_addr);
    unsigned char buffer[BUFFER_SIZE]; // 接收数据的缓冲区
    char target_ip[INET_ADDRSTRLEN]; // 匹配的目标 IP 字符串

    // 创建 UDP 套接字
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    // 设置监听地址和端口
    memset(&listen_addr, 0, sizeof(listen_addr));
    listen_addr.sin_family = AF_INET;
    listen_addr.sin_addr.s_addr = INADDR_ANY;
    listen_addr.sin_port = htons(listen_port);

    // 绑定套接字到指定地址和端口
    if (bind(sockfd, (struct sockaddr *)&listen_addr, sizeof(listen_addr)) < 0) {
        perror("bind");
        close(sockfd);
        exit(EXIT_FAILURE);
    }

    printf("Listening for UDP packets on %s:%d...\n", "0.0.0.0", listen_port);

    while (1) {
        // Receive packet from client
        ssize_t received_size = recvfrom(sockfd, buffer, BUFFER_SIZE, 0, 
                                          (struct sockaddr *)&client_addr, &addr_len);
        if (received_size < 0) {
            perror("recvfrom");
            continue;
        }

        print_ip_info(buffer, received_size); // Print IP header info

        struct iphdr *ip_header = (struct iphdr *)buffer;
        
        // Select IP based on flag: source or destination
        struct in_addr selected_addr;
        if (flag == 0) {
            selected_addr.s_addr = ip_header->saddr; // Use source IP if flag is 0
        } else {
            selected_addr.s_addr = ip_header->daddr; // Use destination IP if flag is 1
        }
        strcpy(target_ip, inet_ntoa(selected_addr)); // Store selected IP as string

        printf("Received packet from %s:%d, selected IP: %s\n",
               inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port), target_ip);
//        printf("forward_targets[0].source_ip:%s\n",forward_targets[0].source_ip);
//        printf("---\n");
//        printf("num_targets:%d\n",num_targets);
//        printf("---\n");

        // Check if selected IP matches any forwarding target
        for (int i = 0; i < num_targets; i++) {
//            printf("---\n");
//            printf("%s\n",(flag == 0 ? forward_targets[i].source_ip : forward_targets[i].destination_ip));
//            printf("%d\n",(flag == 0 ? forward_targets[i].source_ip : forward_targets[i].destination_ip)== 0);
            if (strcmp(target_ip, forward_targets[i].source_ip) == 0) {
            	struct sockaddr_in forward_addr;
                memset(&forward_addr, 0, sizeof(forward_addr));
            	if (flag == 0) {
                forward_addr.sin_family = AF_INET;
                forward_addr.sin_addr.s_addr = inet_addr(forward_targets[i].destination_ip);
                forward_addr.sin_port = htons(forward_port);
                // Forward packet to specified target IP and port
                sendto(sockfd, buffer, received_size, 0, (struct sockaddr *)&forward_addr, sizeof(forward_addr));
                }
		if (flag == 1) {
		    char ip_copy[INET_ADDRSTRLEN];
		    strncpy(ip_copy, forward_targets[i].destination_ip, INET_ADDRSTRLEN);
		    forward_addr.sin_family = AF_INET;
		    forward_addr.sin_port = htons(forward_port);
		    char *last_dot = strrchr(ip_copy, '.');
		    if (last_dot != NULL) {
			snprintf(last_dot + 1, INET_ADDRSTRLEN - (last_dot - ip_copy) - 1, "1");
		    }
		    forward_addr.sin_addr.s_addr = inet_addr(ip_copy);
		    sendto(sockfd, buffer, received_size, 0, (struct sockaddr *)&forward_addr, sizeof(forward_addr));
		    printf("Forwarded packet 1_1 to %s\n",ip_copy);
		}
                printf("Forwarded packet to %s:%d\n", forward_targets[i].destination_ip, forward_port);
                break; // Exit loop after forwarding
            }
        }
    }

    close(sockfd); // 关闭套接字
    free(forward_targets); // 释放转发规则的内存
    return 0;
}

