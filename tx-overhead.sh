
dir=exptdata/tmout10ms

for rl in htb perfiso; do
	for rate in 1000 3000 6000 9000; do
		python tests/tx-overhead.py --rate $rate --dir $dir/rl$rl-r$rate --rl $rl
	done

	for n in 8 16 32 64 128; do
		python tests/tx-overhead.py --rate 100 --dir $dir/rl$rl-r100-n$n -n $n --rl $rl
	done
done

