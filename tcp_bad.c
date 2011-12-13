#include <linux/config.h>
#include <linux/module.h>
#include <net/tcp.h>

/*
 * a very bad tcp that does not reduce its ssthresh, so it always
 * remains in slow-start and never does AI.
 */

u32 default_cwnd = 1000;

/* Do not do halve ssthresh */
u32 tcp_bad_ssthresh(struct sock *sk) {
	struct tcp_sock *tp = tcp_sk(sk);
	return max(tp->snd_cwnd, 2U);
}

void tcp_bad_cong_avoid(struct sock *sk, u32 ack, u32 in_flight) {
	struct tcp_sock *tp = tcp_sk(sk);
	tp->snd_cwnd = min(default_cwnd, tp->snd_cwnd + 1);
}

static struct tcp_congestion_ops bad __read_mostly = {
	.ssthresh = tcp_bad_ssthresh,
	.cong_avoid = tcp_bad_cong_avoid,
	.owner = THIS_MODULE,
	.name = "bad"
};

static int __init tcp_bad_register(void) {
	return tcp_register_congestion_control(&bad);
}

static void __exit tcp_bad_unregister(void) {
	tcp_unregister_congestion_control(&bad);
}

module_init(tcp_bad_register);
module_exit(tcp_bad_unregister);

MODULE_AUTHOR("Vimalkumar");
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("bad TCP");

/* Local Variables: */
/* indent-tabs-mode:t */
/* End: */
