exptid=`date +%b%d-%H:%M`
dir=/tmp/$exptid/incast
time=120

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

basecmd="python tests/scenario.py --time $time -n 14 --run tcpvsudp --exptid $exptid"

for iso in "" "--enabled"; do
for size in 100G; do
	for proto in udp; do
		for mtu in 9000; do
            # WITH ISOLATION
			python tests/genconfig.py --type $proto --traffic incast \
				--size $size --repeat 1000 \
				--inter 5 -n 16 --time 1000 \
				--duration 100s \
				--tenant 2 > ~/vimal/exports/14to1_${size}_${proto}_tenant

			$basecmd --dir $dir/$proto-mtu$mtu-s$size-with$iso $iso \
				--traffic ~/vimal/exports/14to1_${size}_${proto}_tenant \
				--mtu $mtu \

            # WITHOUT ISOLATION
			#python tests/genconfig.py --type $proto --traffic incast \
			#	--size $size --repeat 1000 \
			#	--inter 5 -n 16 --time 1000 > ~/vimal/exports/14to1_${size}_${proto}

			#$basecmd --dir $dir/$proto-mtu$mtu-s$size-without \
			#	--traffic ~/vimal/exports/14to1_${size}_${proto} \
			#	--mtu $mtu
		done
	done
done
done

echo `date` $dir
