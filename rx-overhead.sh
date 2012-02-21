
dir=exptdata/`date +%b%d-%H:%M`/rx
time=120

mkdir -p $dir

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

for rate in 1000 3000 6000 9000; do
	for n in 1 8 16 32 64 128; do
		python tests/rx-overhead.py --rate $rate --dir $dir-with/r$rate-n$n -n $n -t $time
		python tests/rx-overhead.py --rate $rate \
			--dir $dir-without/r$rate-n$n -n $n -t $time --without-vq
	done
done

pushd $dir
python2.6 ~/iso/tests/plots/plot-rx-overhead.py --maxy 45 -o rx.png
popd

echo $dir
