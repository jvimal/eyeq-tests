#include <linux/module.h>
#include <linux/hrtimer.h>
#include <linux/slab.h>

/* From wikipedia */
inline u64 rdtsc(void) {
	u32 lo, hi;
	__asm__ __volatile__ (// serialize
	"xorl %%eax,%%eax \n        cpuid"
	::: "%rax", "%rbx", "%rcx", "%rdx");
    /* We cannot use "=A", since this would use %rax on x86_64 and
	   return only the lower 32bits of the TSC */
    __asm__ __volatile__ ("rdtsc" : "=a" (lo), "=d" (hi));
	return (u64)hi << 32 | lo;
}

ktime_t kstart, kend;
u64 rstart, rend;
const int times = 1000 * 1000 * 10;

void start(void) {
	kstart = ktime_get();
	rstart = rdtsc();
}

void end(const char *fn) {
	u64 us;
	u64 dcycles;

	rend = rdtsc();
	kend = ktime_get();

	us = ktime_us_delta(kend, kstart);
	dcycles = rend - rstart;

	printk(KERN_INFO "%32s: %10d iter, %10llu us (%4llu ns), %20llu cyc (%4llu cyc)\n",
		   fn, times, us, us * 1000 / times, dcycles, dcycles / times);
}

enum hrtimer_restart perf_hrtimer_cb(struct hrtimer *timer) {
    return HRTIMER_NORESTART;
}

void perf_hrtimer_insert(int n) {
    int i;
    ktime_t timeout;
    struct hrtimer *timer;

    /* Just test time it takes to insert n timers */
    struct hrtimer *timers = kmalloc(n * sizeof(struct hrtimer), GFP_USER);
    if(timers == NULL) {
        printk(KERN_INFO "Alloc failed\n");
        return;
    }

    for(i = 0; i < n; i++) {
        timer = &timers[i];
        hrtimer_init(timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
        timer->function = perf_hrtimer_cb;
    }

    /* 10 sec timeout */
    timeout = ktime_set(10, 0);
    start();
    for(i = 0; i < n; i++) {
        timer = &timers[i];
        hrtimer_start(timer, timeout, HRTIMER_MODE_REL);
    }

    for(i = 0; i < n; i++) {
        timer = &timers[i];
        hrtimer_cancel(timer);
    }
    end(__FUNCTION__);

    kfree(timers);
}

void perf_apic_mem_read(void) {
    int i;
    volatile int r;

    /* Warmup */
    for(i = 0; i < 100; i++)
        native_apic_mem_read(APIC_TMICT);

    start();
    for(i = 0; i < times; i++)
        r = native_apic_mem_read(APIC_TMICT);
    end(__FUNCTION__);
}

void perf_apic_mem_write(void) {
    int i;
    volatile int r;

    /* Warmup */
    for(i = 0; i < 100; i++)
        native_apic_mem_read(APIC_TMICT);

    r = native_apic_mem_read(APIC_TMICT);
    start();
    for(i = 0; i < times; i++)
        native_apic_mem_write(APIC_TMICT, r);
    end(__FUNCTION__);
}

static void __iomem *hpet_virt_address;

inline unsigned int hpet_readl(unsigned int a) {
    return readl(hpet_virt_address + a);
}

static inline void hpet_writel(unsigned int d, unsigned int a) {
    writel(d, hpet_virt_address + a);
}

#define HPET_COUNTER 0x0f0
#define HPET_Tn_CMP(n)          (0x108 + 0x20 * n)

void perf_hpet_read(void) {
    int i;
    volatile int r;

    /* This WILL be different on different kernel builds */
    hpet_virt_address = (void *) *(u64 *)(0xffffffff81bab3a0);
    printk(KERN_INFO "hpet_virt_address: %p\n", hpet_virt_address);

    /* Warmup */
    for(i = 0; i < 100; i++)
        r = hpet_readl(HPET_COUNTER);

    start();
    for(i = 0; i < times; i++)
        r = hpet_readl(HPET_COUNTER);
    end(__FUNCTION__);
}

void perf_hpet_write(void) {
    int i;
    volatile int r;

    /* warmup */
    for(i = 0; i < 100; i++)
        r = hpet_readl(HPET_COUNTER);

    start();
    for(i = 0; i < times; i++)
        hpet_writel(r, HPET_Tn_CMP(1));
    end(__FUNCTION__);
}

static int __init hrtimer_register(void) {
    // perf_hrtimer_insert(100000);
    perf_apic_mem_read();
    perf_apic_mem_write();
    perf_hpet_read();
    perf_hpet_write();
    return -1;
}


static void __exit hrtimer_unregister(void) {
	return;
}

module_init(hrtimer_register);
module_exit(hrtimer_unregister);

MODULE_AUTHOR("Vimalkumar");
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Microbenchmark for hrtimer functions");
