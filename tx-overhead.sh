
dir=exptdata/`date +%b%d-%H:%M`/tx/
time=120

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

for rl in perfiso htb; do
	tmout=500000
	for m in 4 16 32 64 128; do
		subdir=rl$rl-r9000-P$m
		python tests/tx-overhead.py --rate 9000 --dir $dir/$subdir --rl $rl -m $m \
			--profile $dir/$subdir/profile \
			-t $time
	done

	for rate in 1000 3000 6000 9000; do
		subdir=rl$rl-r$rate-tmout$tmout
		python tests/tx-overhead.py --rate $rate \
			--dir $dir/$subdir \
			--rl $rl -t $time \
			--profile $dir/$subdir/profile
	done

	for n in 8 16 32 48 64 92; do
		subdir=rl$rl-r100-n$n-tmout$tmout
		python tests/tx-overhead.py --rate 100 --dir $dir/$subdir \
			-n $n --rl $rl -t $time \
			--profile $dir/$subdir/profile
	done
done

pushd $dir
for plot in number rate conn; do
	python2.6 ~/iso/tests/plots/plot-tx-overhead.py -p $plot -o $plot.png
done
popd

echo $dir
