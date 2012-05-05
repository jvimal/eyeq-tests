#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/hrtimer.h>

MODULE_LICENSE("GPL");

#define TIME_TEST_REPEAT 1000000

static struct timespec ts1, ts2, ts3;

static ktime_t kt1, kt2, kt3;

static void print_time_diff(const char* event,
			    struct timespec* t1, struct timespec* t2)
{
  printk(KERN_INFO "%s took %ld ns\n", event,
	 (t2->tv_sec-t1->tv_sec)* 1000000000 + 
	 t2->tv_nsec-t1->tv_nsec);  
  return;
}

static int __init tt_init(void)
{
  int i;

  getnstimeofday(&ts1);
  getnstimeofday(&ts2);
  for (i = 0 ; i < TIME_TEST_REPEAT-2; i++)
    getnstimeofday(&ts3);

  kt1 = ktime_get();
  kt2 = ktime_get();
  for (i = 0 ; i < TIME_TEST_REPEAT-2; i++)
    kt3 = ktime_get();

  print_time_diff("getnstimeofday (1 to 2)", &ts1, &ts2);
  print_time_diff("getnstimeofday (1 to x)", &ts1, &ts3);

  printk(KERN_INFO "ktime_get took %llu ns\n", ktime_to_ns(ktime_sub(kt2, kt1)));
  printk(KERN_INFO "ktime_get (%i x) took %llu ns\n", TIME_TEST_REPEAT, ktime_to_ns(ktime_sub(kt3, kt1))/TIME_TEST_REPEAT);

  return 0;
}

static void __exit tt_exit(void)
{
  printk(KERN_INFO "============================\n");
}

module_init(tt_init);
module_exit(tt_exit);
