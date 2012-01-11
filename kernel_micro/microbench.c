
#include <linux/module.h>
#include <linux/hrtimer.h>
#include <linux/spinlock.h>
#include <linux/jhash.h>
#include <linux/atomic.h>
#include <linux/kthread.h>
#include <linux/delay.h>

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
spinlock_t global_lock;
unsigned long global_flags;
const int times = 1000 * 1000 * 10;

void start(void) {
	/*
	  spin_lock_init(&global_lock);
	  spin_lock_irqsave(&global_lock, global_flags);
	*/
	kstart = ktime_get();
	rstart = rdtsc();
}

void end(const char *fn) {
	u64 us;
	u64 dcycles;

	rend = rdtsc();
	kend = ktime_get();

	/*
	  spin_unlock_irqrestore(&global_lock, global_flags);
	*/

	us = ktime_us_delta(kend, kstart);
	dcycles = rend - rstart;

	printk(KERN_INFO "%32s: %10d iter, %10llu us (%4llu ns), %20llu cyc (%4llu cyc)\n",
		   fn, times, us, us * 1000 / times, dcycles, dcycles / times);
}

void perf_ktime_get(void) {
	ktime_t read;
	int i;
	u64 read_64;

	start();
	for(i = 0; i < times; i++) {
		read = ktime_get();
	    read_64 = *(u64 *)&read;
		read_64++;
	}
	end(__FUNCTION__);
}

void perf_spinlock_irq(void) {
	unsigned long flags;
	spinlock_t lock;
	int i;

	spin_lock_init(&lock);

	start();
	for(i = 0; i < times; i++) {
		spin_lock_irqsave(&lock, flags);
		spin_unlock_irqrestore(&lock, flags);
	}
	end(__FUNCTION__);
}

void perf_spinlock(void) {
	spinlock_t lock;
	int i;

	spin_lock_init(&lock);

	start();
	for(i = 0; i < times; i++) {
		spin_lock(&lock);
		spin_unlock(&lock);
	}
	end(__FUNCTION__);
}

void perf_likely_miss(void) {
	int i;
	u64 count = 0;

	start();
	for(i = 0; i < times; i++) {
		if(likely(i == 0))
			count++;
	}
	end(__FUNCTION__);
}

void perf_likely_hit(void) {
	int i;
	u64 count = 0;

	start();
	for(i = 0; i < times; i++) {
		if(likely(i != 0))
			count++;
	}
	end(__FUNCTION__);
}

void perf_jhash_1word(void) {
	int i;
	u64 data = 0;

	/* Warm up */
	for(i = 0; i < 100; i ++)
		data = jhash_1word(data, 0xdeadbeef);

	start();
	for(i = 0; i < times; i++) {
		data = jhash_1word(data, 0xdeadbeef);
	}
	end(__FUNCTION__);
}

void perf_smp_id(void) {
	int i, cpu;

	/* Warm up */
	for(i = 0; i < 100; i ++)
		cpu = smp_processor_id();

	start();
	for(i = 0; i < times; i++) {
		cpu = smp_processor_id();
	}
	end(__FUNCTION__);
}

void perf_atomic_inc(void) {
	int i;
	atomic_t x;
	atomic_set(&x, 0);
	for(i = 0; i < 100; i++)
		atomic_inc(&x);

	start();
	for(i = 0; i < times; i++) {
		atomic_inc(&x);
	}
	end(__FUNCTION__);
}


int perf_thread_atomic_worker(void *data) {
	atomic_t *var = (atomic_t *)data;
	int i;

	for(i = 0; i < times; i++)
		atomic_inc(var);

	return 0;
}

void perf_thread_shared_atomic(void) {
	struct task_struct *ts[8];
	atomic_t counter;
	int i;
	const int num_cpus = 8;
	atomic_set(&counter, 0);

	start();
	for(i = 0; i < num_cpus; i++) {
		ts[i] = kthread_create(perf_thread_atomic_worker, (void *)&counter, "perf_kthread");
		kthread_bind(ts[i], i);
	}

	for(i = 0; i < num_cpus; i++) {
		if(!IS_ERR(ts[i]))
			wake_up_process(ts[i]);
	}

	for(i = 0; i < num_cpus; i++) {
		kthread_stop(ts[i]);
	}
	end(__FUNCTION__);

	mb();

	printk(KERN_INFO "\t\t\tfinal value: %d (expected: %d)\n",
		   atomic_read(&counter), num_cpus*times);
}


int perf_thread_int_worker(void *data) {
	u64 *var = (u64 *)data;
	int i;

	for(i = 0; i < times; i++)
		*var = 1 + *var;

	return 0;
}

void perf_thread_shared_int(void) {
	struct task_struct *ts[8];
	u64 counter;
	int i;
	const int num_cpus = 8;
	counter = 0;

	start();
	for(i = 0; i < num_cpus; i++) {
		ts[i] = kthread_create(perf_thread_int_worker, (void *)&counter, "perf_kthread");
		kthread_bind(ts[i], i);
	}

	for(i = 0; i < num_cpus; i++) {
		if(!IS_ERR(ts[i]))
			wake_up_process(ts[i]);
	}

	for(i = 0; i < num_cpus; i++) {
		kthread_stop(ts[i]);
	}
	end(__FUNCTION__);

	mb();

	printk(KERN_INFO "\t\t\tfinal value: %llu (expected: %d)\n",
		   counter, num_cpus*times);
}

void perf_thread_separate_atomic(void) {
	struct task_struct *ts[8];
	atomic_t counter[8];
	int i, total=0;
	const int num_cpus = 8;

	start();
	for(i = 0; i < num_cpus; i++) {
		atomic_set(&counter[i], 0);
		ts[i] = kthread_create(perf_thread_atomic_worker, (void *)&counter[i], "perf_kthread");
		kthread_bind(ts[i], i);
	}

	for(i = 0; i < num_cpus; i++) {
		if(!IS_ERR(ts[i]))
			wake_up_process(ts[i]);
	}

	for(i = 0; i < num_cpus; i++) {
		kthread_stop(ts[i]);
	}
	end(__FUNCTION__);

	mb();

	for(i = 0; i < num_cpus; i++) {
		atomic_t *c = &counter[i];
		total += atomic_read(c);
	}

	printk(KERN_INFO "\t\t\tfinal value: %d (expected: %d)\n", total, num_cpus * times);
}


void perf_thread_percpu_atomic(void) {
	struct task_struct *ts[8];
	atomic_t *counter __percpu;
	int i;
	int total = 0;
	const int num_cpus = 8;

	counter = alloc_percpu(atomic_t);
	for(i = 0; i < num_cpus; i++) {
		atomic_t *c = per_cpu_ptr(counter, i);
		atomic_set(c, 0);
	}

	start();
	for(i = 0; i < num_cpus; i++) {
		atomic_t *c = per_cpu_ptr(counter, i);
		ts[i] = kthread_create(perf_thread_atomic_worker, (void *)c, "perf_kthread");
		kthread_bind(ts[i], i);
	}

	for(i = 0; i < num_cpus; i++) {
		if(!IS_ERR(ts[i]))
			wake_up_process(ts[i]);
	}

	for(i = 0; i < num_cpus; i++) {
		kthread_stop(ts[i]);
	}
	end(__FUNCTION__);

	mb();

	for(i = 0; i < num_cpus; i++) {
		atomic_t *c = per_cpu_ptr(counter, i);
		total += atomic_read(c);
	}

	printk(KERN_INFO "\t\t\tfinal value: %d (expected: %d)\n", total, num_cpus * times);
	free_percpu(counter);
}


void perf_rdtsc(void) {
	int i;
	u64 val;

	start();
	for(i = 0; i < times; i++) {
		val += rdtsc();
	}
	end(__FUNCTION__);
}

static int __init microbench_register(void) {
	perf_ktime_get();
	perf_spinlock();
	perf_spinlock_irq();
	perf_likely_miss();
	perf_likely_hit();
	perf_jhash_1word();
	perf_smp_id();
	perf_atomic_inc();
	perf_thread_shared_atomic();
	perf_thread_shared_int();
	perf_thread_separate_atomic();
	perf_thread_percpu_atomic();
	perf_rdtsc();
	return -1;
}

static void __exit microbench_unregister(void) {
	return;
}

module_init(microbench_register);
module_exit(microbench_unregister);

MODULE_AUTHOR("Vimalkumar");
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Microbenchmark for kernel functions");

/* Local Variables: */
/* indent-tabs-mode:t */
/* End: */
