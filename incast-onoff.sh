exptid=`date +%b%d-%H:%M`
dir=/tmp/$exptid/incast-onoff
time=120

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

n=16

basecmd="python tests/scenario.py --time $time -n $n --run tcpvsudp --exptid $exptid"

for onoff in 10us,20us  10us,150us  100us,200us  1ms,2ms  100ms,200ms; do
for iso in "" "--enable"; do
	for proto in udp; do
		for mtu in 9000; do
			python tests/genconfig.py --type $proto --traffic incast \
				--size 100G --repeat -1 \
				--on-off $onoff -n $n --time 1000 \
				--tenant 2 > ~/vimal/exports/${n}to1_${proto}_${onoff}_tenant

			$basecmd --dir $dir/$proto-mtu$mtu-$onoff-n$n-with$iso $iso \
				--traffic ~/vimal/exports/${n}to1_${proto}_${onoff}_tenant \
				--mtu $mtu

			# WITHOUT ISOLATION
			#python tests/genconfig.py --type $proto --traffic incast \
			#--size 100G --repeat -1 \
			#	--on-off $onoff -n $n --time 1000 \
			#	> ~/vimal/exports/${n}to1_${proto}_${onoff}

			#$basecmd --dir $dir/$proto-mtu$mtu-$onoff-n$n-without \
			#	--traffic ~/vimal/exports/${n}to1_${proto}_${onoff} \
			#	--mtu $mtu
		done
	done
done
done

echo `date` $dir
