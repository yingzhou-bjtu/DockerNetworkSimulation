#include "lsdb.h"

#include <string.h>

#include "common.h"


static int32_t lsa_seq = 0x80000001;

int32_t get_lsa_seq() {
	return htonl(lsa_seq++);
}

#define MODX						4102
#define LSA_CHECKSUM_OFFSET			15

uint16_t fletcher16(const uint8_t *data, size_t len) {
    const uint8_t *sp, *ep, *p, *q;
	int c0 = 0, c1 = 0;
	int x, y;

	for (sp = data, ep = sp + len; sp < ep; sp = q) {
		q = sp + MODX;
		if (q > ep) q = ep;
		for (p = sp; p < q; p++) {
			c0 += *p;
			c1 += c0;
		}
		c0 %= 255;
		c1 %= 255;
	}
	x = ((len - LSA_CHECKSUM_OFFSET) * c0 - c1) % 255;
	if (x <= 0) x += 255;
	y = 510 - c0 - x;
	if (y > 255) y -= 255;
	return (x << 8) + y;
}

lsa_header *gen_router_lsa(area *a) {
	uint8_t buff[BUFFER_SIZE];
	lsa_header *lsah = (lsa_header *)buff;
	router_lsa *rlsa = (router_lsa *)(buff + sizeof(lsa_header));
	struct link *l = rlsa->links;
	lsah->age = 0;
	lsah->options = OPTIONS;
	lsah->type = OSPF_ROUTER_LSA;
	lsah->id = myid;
	lsah->ad_router = myid;
	lsah->seq_num = get_lsa_seq();
	rlsa->flags = 0x00;
	rlsa->zero = 0x00;
	

	for (int i = 0; i < a->num_if; ++i) {
		if (a->ifs[i]->num_nbr == 0) {
			/* StubNet */
			l->type = ROUTERLSA_STUB;
			l->id = a->ifs[i]->ip & a->ifs[i]->mask;
			l->data = a->ifs[i]->mask;
			l->tos = 0;
			l->metric = a->ifs[i]->cost;
		} else {
			/* Broadcast */
			if (a->ifs[i]->state == 1) {
				/* TransNet */
				l->type = ROUTERLSA_TRANSIT;
				l->id = a->ifs[i]->dr;
				l->data = a->ifs[i]->ip;
				l->tos = 0;
				l->metric = a->ifs[i]->cost;
			} else {
				/* StubNet */
				l->type = ROUTERLSA_STUB;
				l->id = a->ifs[i]->ip & a->ifs[i]->mask;
				l->data = a->ifs[i]->mask;
				l->tos = 0;
				l->metric = a->ifs[i]->cost;
			}
		}
		
		
		++l;
		
	}
	
	rlsa->num_link = a->num_if;
	size_t len = sizeof(lsa_header) + sizeof(router_lsa) +
				(l - rlsa->links) * sizeof(struct link);
	lsah->length = htons(len);
	lsah->checksum = 0;
	lsah->checksum = htons(fletcher16(buff + sizeof(lsah->age), ntohs(lsah->length) - sizeof(lsah->age)));
	return insert_lsa(a, lsah);
}

int lsah_eql(const lsa_header *a, const lsa_header *b) {
	return a->type == b->type && a->id == b->id && a->ad_router == b->ad_router;
}

/* return value < 0: b is newer, > 0: a is newer , = 0: the same */
int cmp_lsah(const lsa_header *a, const lsa_header *b) {
	//return -1;
	if (a->seq_num != b->seq_num)
		return ntohl(a->seq_num) - ntohl(b->seq_num);
	else
		return ntohs(a->age) - ntohs(b->age);
}

void add_lsah(neighbor *nbr, const lsa_header *lsah) {
	for (int i = 0; i < nbr->num_lsah; ++i)
		if (lsah_eql(&nbr->lsahs[i], lsah)) {
			if (cmp_lsah(&nbr->lsahs[i], lsah) < 0)
				nbr->lsahs[i] = *lsah;
			return;
		}
	nbr->lsahs[nbr->num_lsah++] = *lsah;
}

lsa_header *find_lsa(const area *a, const lsa_header *lsah) {
	for (int i = 0; i < a->num_lsa; ++i)
		if (lsah_eql(a->lsas[i], lsah)) return a->lsas[i];
	return NULL;
}

lsa_header *insert_lsa(area *a, const lsa_header *lsah) {

    // 如果发现 LSA 的 ID 是自己的 ID，检查序列号
    if (lsah->id == myid) {
        // 更新本地序列号
        if (ntohl(lsah->seq_num) > ntohl(get_lsa_seq())) {
            lsa_seq = ntohl(lsah->seq_num);
        }
    }

	int i;
	for (i = 0; i < a->num_lsa; ++i)
		if (lsah_eql(a->lsas[i], lsah)) {
			if (cmp_lsah(a->lsas[i], lsah) < 0) break;
			else return NULL;
		}
	size_t len = ntohs(lsah->length);
	a->lsas[i] = realloc(a->lsas[i], len);
	memcpy(a->lsas[i], lsah, len);
	a->num_lsa += i == a->num_lsa;
	return a->lsas[i];
}

