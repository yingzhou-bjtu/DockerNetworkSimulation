#include "lsu.h"
#include <string.h>
#include "lsdb.h"

//static int current_index = 0; // 用于跟踪当前复制的LSA的起始索引

void process_lsu(area *a, neighbor *nbr, ospf_header *ospfhdr) {
    uint8_t *p = (uint8_t *)ospfhdr + sizeof(ospf_header) + 4;
    int num = ntohl(*((uint32_t *)((uint8_t *)ospfhdr + sizeof(ospf_header))));
    while (num--) {
        lsa_header *lsah = (lsa_header *)p;
        uint16_t sum = ntohs(lsah->checksum);
        lsah->checksum = 0;
        /* check the checksum */
        // if (sum != fletcher16(p + sizeof(lsah->age),
        //             ntohs(lsah->length) - sizeof(lsah->age))) continue;
        lsah->checksum = htons(sum);
        for (int i = 0; i < nbr->num_lsah; ++i)
            if (lsah_eql(nbr->lsahs +i, lsah)) {
                nbr->lsahs[i] = nbr->lsahs[--nbr->num_lsah];
                break;
            }
        /* add it to the ack list */
        nbr->acks[nbr->num_ack++] = *lsah;
        /* insert it to the lsdb */
        insert_lsa(a, lsah);
        p += ntohs(lsah->length);
    }
}

// 生成LSU报文
// void produce_lsu(const area *a, const neighbor *nbr, ospf_header *ospfhdr) {
// 	uint8_t *p = (uint8_t *)ospfhdr + sizeof(ospf_header) + 4;
// 	*((uint32_t *)((uint8_t *)ospfhdr + sizeof(ospf_header))) =
// 			ntohl(nbr->num_lsr);
// 	for (int i = 0; i < nbr->num_lsr; ++i)
// 		for (int j = 0; j < a->num_lsa; ++j)
// 			if (nbr->lsrs[i].ls_type == htonl(a->lsas[j]->type) &&
// 				nbr->lsrs[i].ls_id == a->lsas[j]->id &&
// 				nbr->lsrs[i].ad_router == a->lsas[j]->ad_router) {
// 				size_t len = htons(a->lsas[j]->length);
// 				memcpy(p, a->lsas[j], len);
// 				p += len;
// 				break;
// 			}
// 	ospfhdr->type = OSPF_TYPE_LSU;
// 	ospfhdr->length = htons(p - (uint8_t *)ospfhdr);
// }

void produce_lsu(const area *a, const neighbor *nbr, ospf_header *ospfhdr, int index) {
    uint8_t *p = (uint8_t *)ospfhdr + sizeof(ospf_header) + 4; // 指向LSU报文的LSA列表开始位置
    *((uint32_t *)((uint8_t *)ospfhdr + sizeof(ospf_header))) = htonl(1); // 设置LSA的数量为1

    if (index < a->num_lsa) { // 确保索引在有效范围内
        size_t len = htons(a->lsas[index]->length); // 获取LSA的长度
        memcpy(p, a->lsas[index], len); // 复制LSA到LSU报文中
        p += len; // 移动指针到下一个LSA的位置
    }

    ospfhdr->type = OSPF_TYPE_LSU; // 设置OSPF头部的类型为LSU
    ospfhdr->length = htons(p - (uint8_t *)ospfhdr); // 设置OSPF头部的长度
}


void produce_upd(const area *a, const lsa_header *lsa, ospf_header *ospfhdr) {
    uint8_t *p = (uint8_t *)ospfhdr + sizeof(ospf_header) + 4;
    *((uint32_t *)((uint8_t *)ospfhdr + sizeof(ospf_header))) = ntohl(1);
    size_t len = htons(lsa->length);
    memcpy(p, lsa, len);
    p += len;
    ospfhdr->type = OSPF_TYPE_LSU;
    ospfhdr->length = htons(p - (uint8_t *)ospfhdr);
}
