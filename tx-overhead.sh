
dir=exptdata/`date +%b%d-%H:%M`/tx/
time=120

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

for rl in htb perfiso; do
	tmout=500000
	for m in 4 16 32 64 128; do
		python tests/tx-overhead.py --rate 9000 --dir $dir/rl$rl-r9000-P$m --rl $rl -m $m
	done

	for rate in 1000 3000 6000 9000; do
		python tests/tx-overhead.py --rate $rate \
			--dir $dir/rl$rl-r$rate-tmout$tmout \
			--rl $rl -t $time
	done

	for n in 8 16 32 64 128; do
		subdir=rl$rl-r100-n$n-tmout$tmout
		python tests/tx-overhead.py --rate 100 --dir $dir/$subdir \
			-n $n --rl $rl -t $time
	done
done

echo $dir
