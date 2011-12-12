
dir=exptdata/tx/
time=120

for rl in htb perfiso; do
	if [ $rl == "htb" ]; then
		timeouts=1000000
	else
		timeouts="1000000 3000000"
	fi

	for P in 4 64 256; do
		python tests/tx-overhead.py --rate 9000 --dir $dir/rl$rl-r9000-P$P --rl $rl -P $P
	done

	for rate in 1000 3000 6000 9000; do
		for tmout in $timeouts; do
			python tests/tx-overhead.py --rate $rate --dir $dir/rl$rl-r$rate-tmout$tmout --rl $rl --timeout $tmout -t $time
		done
	done

	for n in 8 16 32 64 128; do
		for tmout in $timeouts; do
			python tests/tx-overhead.py --rate 100 --dir $dir/rl$rl-r100-n$n-tmout$tmout -n $n --rl $rl --timeout $tmout -t $time
		done
	done
done
