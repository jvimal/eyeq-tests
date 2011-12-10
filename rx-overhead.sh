
dir=exptdata/rx

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

for rate in 1000 3000 6000 9000; do
	for n in 1 8 16 32 64 128; do
		python tests/rx-overhead.py --rate $rate --dir $dir/r$rate-n$n -n $n -t 240
		python tests/rx-overhead.py --rate $rate \
			--dir $dir-without/r$rate-n$n -n $n -t 240 --without-vq
	done
done
