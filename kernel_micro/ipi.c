#include <linux/interrupt.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/hrtimer.h>
#include <linux/delay.h>
#include <linux/smp.h>

MODULE_LICENSE("GPL");

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

static struct hrtimer timer;
static ktime_t kstart, kend;
static u64 rstart, rend;
static int times = 100;
static struct call_single_data csd;

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

void ipi_ping(void *info) {
    return;
}

inline void run_test_to(int cpu, int data) {
    smp_call_function_single(cpu, ipi_ping, (void *)data, 1);
}

void run_test(void) {
    int cpu, i;

    for_each_online_cpu(cpu) {
        if(cpu != smp_processor_id()) {
            printk(KERN_INFO "cpu %d to cpu %d\n", smp_processor_id(), cpu);
            start();
            for(i = 0; i < times; i++) {
                run_test_to(cpu, i);
            }
            end(__FUNCTION__);
        }
    }
}

static int __init ipi_init(void)
{
    csd.func = ipi_ping;
    csd.info = &csd;
    csd.flags = 0;

    run_test();

    return -1;
}

static void __exit ipi_exit(void)
{

}

module_init(ipi_init);
module_exit(ipi_exit);
