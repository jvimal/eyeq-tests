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

typedef void (*sirq_handler_t)(struct softirq_action *);

static DEFINE_PER_CPU(int, is_it_kk);
static struct hrtimer timer;
static ktime_t start, end;
static u64 start_tsc, end_tsc;
static int times = 10;
static sirq_handler_t old_handler;

static struct softirq_action* table = (struct softirq_action*) 0xffffffff81a02080;

static void kk_action(struct softirq_action* a)
{
  if(__this_cpu_read(is_it_kk))
  {
    __this_cpu_write(is_it_kk, 0);
    end = ktime_get();
    end_tsc = rdtsc();

    printk(KERN_INFO "del_us = %llu, del_tsc = %llu\n", ktime_us_delta(end, start), (end_tsc - start_tsc));
    printk(KERN_INFO "Hihi cpu=%d\n", smp_processor_id());
    if(times > 0) {
        times--;
        hrtimer_start(&timer, ktime_set(0, 100*1000), HRTIMER_MODE_REL_PINNED);
    }
  }
  old_handler(a);
}

enum hrtimer_restart kk_hrtimer_cb(struct hrtimer *timer) {
  __this_cpu_write(is_it_kk, 1);
  or_softirq_pending(KK_NR);
  printk(KERN_INFO "scheduled on cpu %d\n", smp_processor_id());
  start = ktime_get();
  start_tsc = rdtsc();
  return HRTIMER_NORESTART;
}

static int __init kk_init(void)
{
  ktime_t dt;

  asm("cli");
  old_handler = table[KK_NR].action;
  table[KK_NR].action = kk_action;
  smp_wmb();
  asm("sti");

  hrtimer_init(&timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL_PINNED);
  timer.function = kk_hrtimer_cb;

  dt = ktime_set(0, 50 * 1000);
  hrtimer_start(&timer, dt, HRTIMER_MODE_REL);
  return 0;
}

static void __exit kk_exit(void)
{
  hrtimer_cancel(&timer);
  asm("cli");
  table[KK_NR].action = old_handler;
  smp_wmb();
  asm("sti");
}

module_init(kk_init);
module_exit(kk_exit);
