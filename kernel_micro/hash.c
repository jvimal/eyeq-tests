#include <linux/module.h>
#include <linux/jhash.h>

#define MAX_BUCKETS (1025)

unsigned int seed = 0xdeadbeef;
unsigned int count[MAX_BUCKETS];
int ntenants, nbuckets;

MODULE_PARM_DESC(ntenants, "Number of tenants");
module_param(ntenants, int, 0);

MODULE_PARM_DESC(buckets, "Number of buckets");
module_param(nbuckets, int, 0);

static u32 ipaddr(u32 a, u32 b, u32 c, u32 d) {
    return (a << 24) | (b << 16) | (c << 8) | d;
}

static int __init hash_register(void) {
    int i, hsh, ip;

    if(ntenants <= 0)
        ntenants = 32;

    if(nbuckets <= 0)
        nbuckets = 256;

    if(nbuckets >= 1024)
        nbuckets = 1024;

    for(i = 0; i < ntenants; i++) {
        ip = ipaddr(11, 0, i+1, 1);
        hsh = jhash_1word(ip, seed) % nbuckets;
        count[hsh]++;
    }

    for(i = 0; i < nbuckets; i++) {
        if(count[i])
            printk(KERN_INFO "[%3d] %3d\n", i, count[i]);
    }

    return -1;
}


static void __exit hash_unregister(void) {
	return;
}

module_init(hash_register);
module_exit(hash_unregister);

MODULE_AUTHOR("Vimalkumar");
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Testing hash lengths");
