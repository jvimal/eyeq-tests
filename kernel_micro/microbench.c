
#include <linux/module.h>
#include <linux/hrtimer.h>
#include <linux/spinlock.h>
#include <linux/jhash.h>
#include <linux/atomic.h>
#include <linux/kthread.h>
#include <linux/delay.h>
#include <linux/completion.h>
#include <linux/slab.h>
#include <linux/hrtimer.h>
#include <linux/net.h>
#include <linux/interrupt.h>
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

inline u64 rdtsc_alone(void) {
	u32 lo, hi;
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
	volatile ktime_t read;
	int i;

	start();
	for(i = 0; i < times; i++) {
		read = ktime_get();
	}
	end(__FUNCTION__);

	start();
	for(i = 0; i < times; i++)
		asm ("nop");
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

void perf_rdtsc_alone(void) {
	int i;
	u64 val;

	start();
	for(i = 0; i < times; i++) {
		val += rdtsc_alone();
	}
	end(__FUNCTION__);
}

u64 val[1000];
void perf_rdtsc_loop(void) {
	int i;
	u64 a, b;

	for(i = 0; i < 1000; i++) {
		a = rdtsc_alone();
		b = rdtsc_alone();
		val[i] = b - a;
	}
	printk(KERN_INFO "Loop rdtsc: %s\n", __FUNCTION__);
	for(i = 0; i < 1000; i++)
		printk(KERN_INFO "val[%d] = %llu\n", i, val[i]);
}

void perf_ktimeget_loop(void) {
	int i;
	u64 a, b;
	volatile ktime_t ret;

	for(i = 0; i < 1000; i++) {
		a = rdtsc_alone();
		ret = ktime_get();
		b = rdtsc_alone();
		val[i] = b - a;
	}

	printk(KERN_INFO "Loop ktime_get: %s\n", __FUNCTION__);
	for(i = 0; i < 100; i++)
		printk(KERN_INFO "val[%d] = %llu\n", i, val[i]);
}

void perf_ktimeget_loop2(void) {
	int i;
	volatile ktime_t ret1, ret2;

	for(i = 0; i < 1000; i++) {
		ret1 = ktime_get();
		ret2 = ktime_get();
		val[i] = ktime_sub(ret2, ret1).tv64;
	}

	printk(KERN_INFO "Loop ktime_get: %s\n", __FUNCTION__);
	for(i = 0; i < 100; i++)
		printk(KERN_INFO "val[%d] = %llu\n", i, val[i]);
}


/*
 * Stressing hrtimers
 */

struct timer_obj {
	struct hrtimer timer;
	ktime_t start;
	ktime_t end;
}*timers;

DECLARE_COMPLETION(compl);
atomic_t completed;
int timer_latency[100];

enum hrtimer_restart perf_timer_cb(struct hrtimer *timer) {
	struct timer_obj *tobj = container_of(timer, struct timer_obj, timer);
	tobj->end = ktime_get();

	if(atomic_dec_and_test(&completed)) {
		complete(&compl);
	}

	return HRTIMER_NORESTART;
}

void perf_timer(int n, int dt_ns) {
	int i;
	ktime_t timeout = ktime_set(0, dt_ns);
	u64 latency_us;
	int total = 0;

	atomic_set(&completed, n);
	timers = kmalloc(n * sizeof(struct timer_obj), GFP_KERNEL);
	for(i = 0; i < 1000; i++)
		timer_latency[i] = 0;

	if(timers == NULL) {
		printk(KERN_INFO "Timer initialisation failed\n");
		return;
	}

	for(i = 0; i < n; i++) {
		hrtimer_init(&timers[i].timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
		timers[i].timer.function = perf_timer_cb;
	}

	start();
	for(i = 0; i < n; i++) {
		timeout = ktime_set(0, dt_ns);// + net_random() % 1000);
		timers[i].start = ktime_get();
		hrtimer_start(&timers[i].timer, timeout, HRTIMER_MODE_REL);
	}

	wait_for_completion(&compl);
	end(__FUNCTION__);

	for(i = 0; i < n; i++) {
		hrtimer_cancel(&timers[i].timer);
		latency_us = ktime_us_delta(timers[i].end, timers[i].start);
		if(latency_us >= 999)
			latency_us = 999;
		timer_latency[latency_us]++;
	}

	printk(KERN_INFO "Timer for %d us, fires at\n", dt_ns);
	for(i = 0; i < 1000; i++) {
		if(timer_latency[i] > 0) {
			total += timer_latency[i];
			printk(KERN_INFO " %4d us: %5d\n", i, timer_latency[i]);
		}
	}
	printk(KERN_INFO "Total timers: %d\n", total);

	kfree(timers);
}

void perf_timer_long(int repeat) {
	while(repeat--) {
		perf_timer(8 * 1024, 10000);
	}
}



/*
 * The goal is to increment all the dummy_q counters to a target value.
 * Increments are done every timer callback.
 * The timer enqueues tasklet which increments the counter.
 *
 * Strategies:
 * per-queue, per-rl timer? (done)
 * per-rl timer? (done)
 * per-cpu timer?
 * global timer?
 * per-cpu thread that sleeps for some microsec...
 * thread that sleeps for some microsec?  (same as global timer?...)
 */
struct dummy_q {
	int counter;
	struct hrtimer timer;
	struct tasklet_struct tasklet;
	struct completion compl;
};

struct dummy_rl {
	struct __percpu dummy_q *q;

	int counter;
	struct hrtimer timer;
	struct tasklet_struct tasklet;
	struct completion compl;
};

struct dummy_rl *rls;
ktime_t kt;
int dt_us = 10, nrl = 32, ntarget = 10000;
int dt_work = 1;
struct task_struct *tasks[8];

struct percpu_block {
	struct hrtimer timer;
	struct completion compl;
	struct tasklet_struct tasklet;
} __percpu *cpu_block;

atomic_t thread_count;
struct completion thread_complete;

inline void perf_work(void) {
	ktime_t start = ktime_get(), now;
	while(1) {
		now = ktime_get();
		if(unlikely(ktime_us_delta(now, start) >= dt_work))
			break;
		cpu_relax();
	}
	return;
}

/* Queue based tasklet */
void perf_tasklet(unsigned long _q) {
	struct dummy_q *q = (struct dummy_q *)_q;
	struct hrtimer *timer = &q->timer;

	q->counter--;
	perf_work();
	hrtimer_add_expires(timer, kt);
	hrtimer_restart(timer);
}

enum hrtimer_restart perf_timer_cb_perq(struct hrtimer *timer) {
	struct dummy_q *q = container_of(timer, struct dummy_q, timer);
	if(q->counter <= 0) {
		complete(&q->compl);
		return HRTIMER_NORESTART;
	}

	tasklet_schedule(&q->tasklet);
	return HRTIMER_NORESTART;
}

/* RL based tasklet */
void perf_rl_tasklet(unsigned long _rl) {
	struct dummy_rl *rl = (struct dummy_rl *)_rl;
	struct hrtimer *timer = &rl->timer;
	int cpu;

	rl->counter--;
	for_each_online_cpu(cpu) {
		struct dummy_q *q = per_cpu_ptr(rl->q, cpu);
		q->counter--;
		perf_work();
	}

	hrtimer_add_expires(timer, kt);
	hrtimer_restart(timer);
}

enum hrtimer_restart perf_timer_cb_perrl(struct hrtimer *timer) {
	struct dummy_rl *rl = container_of(timer, struct dummy_rl, timer);
	if(rl->counter <= 0) {
		complete(&rl->compl);
		return HRTIMER_NORESTART;
	}

	tasklet_schedule(&rl->tasklet);
	return HRTIMER_NORESTART;
}


/* CPU based tasklet */
void perf_cpu_tasklet(unsigned long cpu) {
	int i, ok = 0;
	struct percpu_block *block = per_cpu_ptr(cpu_block, cpu);

	for(i = 0; i < nrl; i++) {
		struct dummy_rl *rl = &rls[i];
		struct dummy_q *q = per_cpu_ptr(rl->q, cpu);
		q->counter--;
		perf_work();
		if(q->counter <= 0)
			ok = 1;
	}

	if(!ok) {
		struct hrtimer *timer = &block->timer;
		hrtimer_add_expires(timer, kt);
		hrtimer_restart(timer);
	} else {
		struct completion *compl = &block->compl;
		complete(compl);
	}
}

enum hrtimer_restart perf_timer_cb_percpu(struct hrtimer *timer) {
	struct percpu_block *block = container_of(timer, struct percpu_block, timer);
	tasklet_schedule(&block->tasklet);
	return HRTIMER_NORESTART;
}

int perf_timer_2_thread(void *_) {
	int cpu = smp_processor_id();
	int i;

	kt = ktime_set(0, dt_us * 1000);

	for(i = 0; i < nrl; i++) {
		struct dummy_rl *rl = &rls[i];
		struct dummy_q *q = per_cpu_ptr(rl->q, cpu);
		hrtimer_start(&q->timer, kt, HRTIMER_MODE_REL);
	}

	for(i = 0; i < nrl; i++) {
		struct dummy_rl *rl = &rls[i];
		struct dummy_q *q = per_cpu_ptr(rl->q, cpu);
		wait_for_completion(&q->compl);
	}

	if(atomic_dec_and_test(&thread_count))
		complete(&thread_complete);

	do_exit(0);
	return 0;
}

int perf_timer_3_thread(void *_) {
	int i;
	int cpu = smp_processor_id();
	int num_cpus = 8, len = nrl/num_cpus;

	kt = ktime_set(0, dt_us * 1000);
	for(i = 0; i < len; i++) {
		struct dummy_rl *rl = &rls[cpu * len + i];
		hrtimer_start(&rl->timer, kt, HRTIMER_MODE_REL);
	}

	for(i = 0; i < len; i++) {
		struct dummy_rl *rl = &rls[cpu * len + i];
		wait_for_completion(&rl->compl);
	}

	if(atomic_dec_and_test(&thread_count))
		complete(&thread_complete);

	do_exit(0);
	return 0;
}

int perf_timer_4_thread(void *_) {
	int cpu = smp_processor_id();
	struct percpu_block *block;
	struct hrtimer *timer;
	struct completion *compl;

	kt = ktime_set(0, dt_us * 1000);
	block = per_cpu_ptr(cpu_block, cpu);
	timer = &block->timer;
	compl = &block->compl;

	hrtimer_start(timer, kt, HRTIMER_MODE_REL);
	wait_for_completion(compl);

	if(atomic_dec_and_test(&thread_count))
		complete(&thread_complete);

	do_exit(0);
	return 0;
}

int perf_timer_5_thread(void *_) {
	int cpu = smp_processor_id();
	int ok = 0;
	int i;

	kt = ktime_set(0, dt_us * 1000);

	while(!ok) {
		for(i = 0; i < nrl; i++) {
			struct dummy_rl *rl = &rls[i];
			struct dummy_q *q = per_cpu_ptr(rl->q, cpu);
			q->counter--;
			perf_work();
			if(q->counter <= 0)
				ok = 1;
		}
		usleep_range(dt_us, dt_us);
	}

	if(atomic_dec_and_test(&thread_count))
		complete(&thread_complete);

	do_exit(0);
	return 0;
}

void perf_timer_2(void) {
	int i, nrlfree, cpu;
	int num_cpus = 8;

	dt_work = dt_us/10;
	printk(KERN_INFO "***************** nrl=%d, ntarget=%d, dt_us=%d, dt_work=%d\n", nrl, ntarget, dt_us, dt_work);
	/* Alloc rls */
	rls = kmalloc(nrl * sizeof(struct dummy_rl), GFP_KERNEL);
	if(rls == NULL) {
		printk(KERN_INFO "Couldn't allocate dummy rate limiters\n");
		return;
	}

	/* Init rls */
	for(i = 0; i < nrl; i++) {
		struct dummy_rl *rl = &rls[i];
		rl->q = alloc_percpu(struct dummy_q);
		hrtimer_init(&rl->timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
		rl->timer.function = perf_timer_cb_perrl;
		tasklet_init(&rl->tasklet, perf_rl_tasklet, (unsigned long)rl);
		rl->counter = ntarget;
		init_completion(&rl->compl);

		if(rl->q == NULL) {
			nrlfree = i-1;
			goto free_rl;
		}

		for_each_online_cpu(cpu) {
			struct dummy_q *q = per_cpu_ptr(rl->q, cpu);
			q->counter = ntarget;
			init_completion(&q->compl);
			hrtimer_init(&q->timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
			tasklet_init(&q->tasklet, perf_tasklet, (unsigned long)q);
			q->timer.function = perf_timer_cb_perq;
		}
	}


	/* Strat 1: per-queue per-RL timer */
	printk(KERN_INFO "Timer per queue\n");
	atomic_set(&thread_count, num_cpus);
	init_completion(&thread_complete);

	for(i = 0; i < num_cpus; i++) {
		tasks[i] = kthread_create(perf_timer_2_thread, (void *)NULL, "perf_kthread");
		kthread_bind(tasks[i], i);
	}

	start();
	for(i = 0; i < num_cpus; i++) {
		if(!IS_ERR(tasks[i]))
			wake_up_process(tasks[i]);
	}

	wait_for_completion(&thread_complete);
	end(__FUNCTION__);
	mdelay(1);

	/* Reset */
#define RESET do {												\
		for(i = 0; i < nrl; i++) {								\
			struct dummy_rl *rl = &rls[i];						\
			rl->counter = ntarget;								\
			hrtimer_cancel(&rl->timer);							\
			tasklet_kill(&rl->tasklet);							\
																\
			for_each_online_cpu(cpu) {							\
				struct dummy_q *q = per_cpu_ptr(rl->q, cpu);	\
				q->counter = ntarget;							\
				hrtimer_cancel(&q->timer);						\
				tasklet_kill(&q->tasklet);						\
			}													\
		}														\
		atomic_set(&thread_count, num_cpus);					\
		init_completion(&thread_complete);						\
	} while(0)

	RESET;

	/* Strat 2: per-RL timer */
	printk(KERN_INFO "Timer per RL\n");

	for(i = 0; i < num_cpus; i++) {
		tasks[i] = kthread_create(perf_timer_3_thread, (void *)NULL, "perf_kthread");
		kthread_bind(tasks[i], i);
	}

	start();
	for(i = 0; i < num_cpus; i++) {
		if(!IS_ERR(tasks[i]))
			wake_up_process(tasks[i]);
	}

	wait_for_completion(&thread_complete);
	end(__FUNCTION__);
	mdelay(1);

	RESET;

	/* Strat 3: per-cpu timer */
	printk(KERN_INFO "Timer per CPU\n");

	cpu_block = alloc_percpu(struct percpu_block);
	if(cpu_block == NULL)
		goto fail_percpu;

	for(i = 0; i < num_cpus; i++) {
		struct percpu_block *block = per_cpu_ptr(cpu_block, i);
		struct hrtimer *timer = &block->timer;
		struct completion *compl = &block->compl;
		struct tasklet_struct *task = &block->tasklet;

		tasks[i] = kthread_create(perf_timer_4_thread, (void *)NULL, "perf_kthread");
		kthread_bind(tasks[i], i);

		hrtimer_init(timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
		timer->function = perf_timer_cb_percpu;
		tasklet_init(task, perf_cpu_tasklet, (unsigned long)i);
		init_completion(compl);
	}

	start();
	for(i = 0; i < num_cpus; i++) {
		if(!IS_ERR(tasks[i]))
			wake_up_process(tasks[i]);
	}

	wait_for_completion(&thread_complete);
	end(__FUNCTION__);
	mdelay(1);

	for(i = 0; i < num_cpus; i++) {
		struct percpu_block *block = per_cpu_ptr(cpu_block, i);
		struct hrtimer *timer = &block->timer;
		struct tasklet_struct *task = &block->tasklet;

		hrtimer_cancel(timer);
		tasklet_kill(task);
	}

 fail_percpu:
	/* Strat 4: per-cpu thread */
	RESET;

	printk(KERN_INFO "Thread per cpu\n");

	for(i = 0; i < num_cpus; i++) {
		tasks[i] = kthread_create(perf_timer_5_thread, (void *)NULL, "perf_kthread");
		kthread_bind(tasks[i], i);
	}

	start();
	for(i = 0; i < num_cpus; i++) {
		if(!IS_ERR(tasks[i]))
			wake_up_process(tasks[i]);
	}

	wait_for_completion(&thread_complete);
	end(__FUNCTION__);
	mdelay(1);

	nrlfree = nrl;
 free_rl:
	for(i = 0; i < nrlfree; i++) {
		struct dummy_rl *rl = &rls[i];

		for_each_online_cpu(cpu) {
			struct dummy_q *q = per_cpu_ptr(rl->q, cpu);
			hrtimer_cancel(&q->timer);
			tasklet_kill(&q->tasklet);
		}

		free_percpu(rl->q);
		hrtimer_cancel(&rl->timer);
		tasklet_kill(&rl->tasklet);
	}

	kfree(rls);
}

MODULE_PARM_DESC(dt_us, "Work time (us, default: 1)");
module_param(dt_work, int, 0);

MODULE_PARM_DESC(dt_us, "Timer interval (us, default: 10)");
module_param(dt_us, int, 0);

MODULE_PARM_DESC(nrl, "Number of rate limiters (default: 32)");
module_param(nrl, int, 0);

MODULE_PARM_DESC(ntarget, "Target countdown (default: 10000)");
module_param(ntarget, int, 0);

static int __init microbench_register(void) {
#if 0
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
#endif
	perf_rdtsc();
	perf_rdtsc_alone();
	perf_rdtsc_loop();
	perf_ktimeget_loop();
	perf_ktimeget_loop2();

	perf_ktime_get();

	/*
	perf_timer_long(100);
	perf_timer_2();
	*/
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
