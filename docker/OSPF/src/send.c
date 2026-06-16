#include "send.h"

#include "lsack.h"
#include "common.h"
#include "dd.h"
#include "hello.h"
#include "io.h"
#include "lsdb.h"
#include "lsr.h"
#include "lsu.h"
#include "nsm.h"
#include <string.h>  
#include <stdio.h>  

#define HASH_TABLE_SIZE 256  // 定义哈希表的大小
#define INET_ADDRSTRLEN 16  // 根据实际长度定义

typedef struct NeighborStatus {
    char id_str[INET_ADDRSTRLEN];  // 邻居的IP地址字符串
    int status;                   // 状态，0表示掉线，1表示在线
} NeighborStatus;

// 定义一个大数组来存储所有的哈希表
NeighborStatus **hash_tables;  // 指向哈希表数组的指针
#define MAX_INTERFACES 256  // 假设的最大接口数量
NeighborStatus hash_table_array[MAX_INTERFACES][HASH_TABLE_SIZE];  // 大数组

// 简单的哈希函数，可以根据实际情况进行优化
unsigned int hash_function(const char *str, int interface_index) {
    unsigned int hash = 0;
    while (*str) {
        hash = (hash * 31 + *str) + interface_index;  // 添加接口索引到哈希计算
        str++;
    }
    return hash % HASH_TABLE_SIZE;
}

// 插入或更新接口的邻居状态
void insert_or_update_neighbor(int interface_index, const char *id_str, int status) {
    unsigned int index = hash_function(id_str, interface_index);  // 传递接口索引
    if (strlen(hash_tables[interface_index][index].id_str) == 0) {  // 检查桶是否为空
        // 桶是空的，可以直接插入
        strncpy(hash_tables[interface_index][index].id_str, id_str, INET_ADDRSTRLEN);
    	hash_tables[interface_index][index].status = status; 
    } else {
        // 桶不为空，更新状态
        if (strcmp(hash_tables[interface_index][index].id_str, id_str) == 0) {
            hash_tables[interface_index][index].status = status;
        }
    }
}

// 打印接口的哈希表
void print_interface_hash_table(int interface_index) {
    for (int i = 0; i < HASH_TABLE_SIZE; i++) {
        if (strlen(hash_tables[interface_index][i].id_str) > 0) {  // 检查桶是否为空
            printf("interface_index:%d %s: %s\n", interface_index, hash_tables[interface_index][i].id_str, hash_tables[interface_index][i].status ? "Online" : "Offline");
            
            if (hash_tables[interface_index][i].status == 0)
            {
            	        for (int a = 0; a < num_if; ++a) {
			    for (int b = 0; b < ifs[a].a->num_lsa; ++b) {
				char id_str[INET_ADDRSTRLEN];

				// 将 IP 地址格式化为字符串
				inet_ntop(AF_INET, &(struct in_addr){ifs[a].a->lsas[b]->id}, id_str, INET_ADDRSTRLEN);
				if(strcmp(hash_tables[interface_index][i].id_str, id_str) == 0)              
						{
						// 打印 LSA 头部信息
						printf("------------------------------------------------------\n");
						printf("Down LSA #%d:", b);
						printf("  LSA Type: %d", ifs[a].a->lsas[b]->type);
						printf("  LSA ID: %s", id_str);
						printf("  LSA Age: %d\n", ifs[a].a->lsas[b]->age);
						printf("------------------------------------------------------\n");
						ifs[a].a->lsas[b]->age = 1;
						}
				}
			}
            }
            
        }
    }
    //printf("\n");
}

// 打印所有接口的哈希表
void print_all_hash_tables() {
    for (int i = 0; i < num_if; i++) {
        //printf("Table for interface %d:\n", i);
        print_interface_hash_table(i);
    }
}

void *send_loop(void *p) {
	uint8_t buf[BUFFER_SIZE];
	
	// 分配一个大数组来存储所有的哈希表
	    hash_tables = calloc(MAX_INTERFACES, sizeof(NeighborStatus *));
	    if (hash_tables == NULL) {
		fprintf(stderr, "Memory allocation failed for hash tables\n");
		exit(EXIT_FAILURE);
	    }
	    for (int i = 0; i < MAX_INTERFACES; i++) {
		hash_tables[i] = hash_table_array[i];
	    }

	    // 初始化每个接口的哈希表
	    for (int i = 0; i < num_if; i++) {
		for (int j = 0; j < HASH_TABLE_SIZE; j++) {
		    hash_tables[i][j].status = 0;  // 将状态设置为0
		    hash_tables[i][j].id_str[0] = '\0';  // 清空字符串
		}
	    }

	
	while (*(int *)p) {
	
					// 重置
					for (int i = 0; i < num_if; ++i) {
					    for (int j = 0; j < HASH_TABLE_SIZE; j++) {
						hash_tables[i][j].status = 0;  // 将状态设置为0
					    }
					}
	
	
		/* BUG: mutex absent in critical area */
		//printf(" Num_if: %d \n", num_if);
		for (int i = 0; i < num_if; ++i) {
		
		  	    		
		
			/* delete neighbors out of date */
			neighbor **p = &ifs[i].nbrs;
			for (neighbor *q = *p; q; q = *p) {
			

					char id_str[INET_ADDRSTRLEN];
					// 将 IP 地址格式化为字符串
					inet_ntop(AF_INET, &(struct in_addr){q->router_id}, id_str, INET_ADDRSTRLEN);		
					
					
				    if (++q->inact_timer >= ifs[i].dead_interval) {
					--ifs[i].num_nbr;
					printf(" Neighbor: %s is down!!!\n", id_str);
					insert_or_update_neighbor(i, id_str, 0);  // 更新状态为掉线
					
					for (int a = 0; a < num_if; ++a) {
					    for (int b = 0; b < ifs[a].a->num_lsa; ++b) {
						char id_str1[INET_ADDRSTRLEN];

						// 将 IP 地址格式化为字符串
						inet_ntop(AF_INET, &(struct in_addr){ifs[a].a->lsas[b]->id}, id_str1, INET_ADDRSTRLEN);
						if(strcmp(id_str, id_str1) == 0)              
								{
								// 打印 LSA 头部信息
								printf("------------------------------------------------------\n");
								printf("Down LSA #%d:", b);
								printf("  LSA Type: %d", ifs[a].a->lsas[b]->type);
								printf("  LSA ID: %s", id_str);
								printf("  LSA Age: %d\n", ifs[a].a->lsas[b]->age);
								printf("------------------------------------------------------\n");
								//ifs[a].a->lsas[b]->age = 1;
								}
						}
					}
					
					*p = q->next;
					free(q);
				    } else {
					insert_or_update_neighbor(i, id_str, 1); // 更新状态为在线
					p = &q->next; // 只有当邻居没有被移除时，才移动p指针
				    }
			}
			
			
			/* send hello packet periodically */
			if (++ifs[i].hello_timer >= ifs[i].hello_interval) {
				ifs[i].hello_timer = 0;
				produce_hello(ifs + i,
							  (ospf_header *)(buf + sizeof(struct iphdr)));
				send_ospf(ifs + i, (struct iphdr *)buf, all_spf_routers);
			}

			for (neighbor *p = ifs[i].nbrs; p; p = p->next) {
				if (++p->rxmt_timer >= ifs[i].rxmt_interval) {
					p->rxmt_timer = 0;
					/* send dd packet */
					// if (p->state == S_ExStart || p->state == S_Exchange) {
					// 	produce_dd(ifs + i, p,
					// 			   (ospf_header *)(buf + sizeof(struct iphdr)));
					// 	send_ospf(ifs + i, (struct iphdr *)buf, p->ip);
					// 	if (!p->master && !p->more)
					// 		add_event(ifs + i, p, E_ExchangeDone);
					// }
					if (p->state == S_ExStart || p->state == S_Exchange) {
                        for (int rt = 0; rt < ifs[i].a->num_lsa; rt++)
                        {
                            produce_dd1(ifs + i, p,
                                    (ospf_header *)(buf + sizeof(struct iphdr)), rt);
                            send_ospf(ifs + i, (struct iphdr *)buf, p->ip);
                        }
						if (!p->master && !p->more)
							add_event(ifs + i, p, E_ExchangeDone);
					}
					/* send lsr packet */
					if (p->state == S_Exchange || p->state == S_Loading) {
					//-------------------------------------------------------
					//printf("*****ifs[i].a->num_lsa: %d\n", ifs[i].a->num_lsa);
						if (p->num_lsah) {
							produce_lsr(p, (ospf_header *)(buf + sizeof(struct iphdr)));
							send_ospf(ifs + i, (struct iphdr *)buf, p->ip);
						} else {
							add_event(ifs + i, p, E_LoadingDone);
						}
					}
					/* send lsu packet */
					// if (p->num_lsr) {
					// 	produce_lsu(ifs[i].a, p,
					// 			(ospf_header *)(buf + sizeof(struct iphdr)));
					// 	send_ospf(ifs + i, (struct iphdr *)buf, p->ip);
					// }

					printf("*****ifs[i].a->num_lsa: %d\n", ifs[i].a->num_lsa);
                    printf("*****p->num_lsr: %d\n", p->num_lsr);
				
					if (p->num_lsr || p->state == S_Exchange || p->state == S_Loading || p->state == S_Full) {
						for (int rt = 0; rt < ifs[i].a->num_lsa; rt++){
							produce_lsu(ifs[i].a, p, (ospf_header *)(buf + sizeof(struct iphdr)), rt);
							send_ospf(ifs + i, (struct iphdr *)buf, p->ip);
						}
					}

					if (rt_lsa && p->state == S_Full) {
						produce_upd(ifs[i].a, rt_lsa,
								(ospf_header *)(buf + sizeof(struct iphdr)));
						send_ospf(ifs + i, (struct iphdr *)buf, p->ip);
						rt_lsa = NULL;
					}
				}
				/* send lsack packet */
				if (p->state >= S_Exchange && p->num_ack) {
					produce_ack(p, (ospf_header *)(buf + sizeof(struct iphdr)));
					send_ospf(ifs + i, (struct iphdr *)buf, p->ip);
					p->num_ack = 0;
				}
			}
		//print_interface_hash_table(i);
		}
		
        	print_all_hash_tables();		
		
		sleep(1);
	}
	
	return NULL;
}
