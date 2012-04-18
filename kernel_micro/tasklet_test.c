#include <linux/interrupt.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/hrtimer.h>
#include <linux/delay.h>

MODULE_LICENSE("GPL");

#define KK_NR 4

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
static ktime_t start, end;
static u64 start_tsc, end_tsc;
static int times = 10;
static struct tasklet_struct tasklet;

void kk_tasklet(unsigned long arg) {
    end = ktime_get();
    end_tsc = rdtsc();
    printk(KERN_INFO "del_us %llu    del_tsc %llu\n", ktime_us_delta(end, start), end_tsc-start_tsc);
}

enum hrtimer_restart kk_hrtimer_cb(struct hrtimer *timer) {
  printk(KERN_INFO "scheduled on cpu %d\n", smp_processor_id());
  start = ktime_get();
  start_tsc = rdtsc();
  tasklet_schedule(&tasklet);
  return HRTIMER_NORESTART;
}

static int __init kk_init(void)
{
  ktime_t dt;

  tasklet_init(&tasklet, kk_tasklet, 0);
  hrtimer_init(&timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL_PINNED);
  timer.function = kk_hrtimer_cb;

  dt = ktime_set(0, 50 * 1000);
  hrtimer_start(&timer, dt, HRTIMER_MODE_REL);
  return 0;
}

static void __exit kk_exit(void)
{
  hrtimer_cancel(&timer);
}

module_init(kk_init);
module_exit(kk_exit);
