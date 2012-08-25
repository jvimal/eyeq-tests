exptid=`date +%b%d-%H:%M`
dir=/tmp/$exptid/incast-onoff-latency
time=120

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

n=3

basecmd="python tests/scenario.py --time $time -n $n --run tcpvsudp --exptid $exptid"

for tcptest in latency; do
for rrsize in 1,1 10000,10000; do
for onoff in 5ms,20ms; do
for iso in "" "--enable"; do
	for proto in udp; do
		for mtu in 9000; do
			python tests/genconfig.py --type $proto --traffic incast \
				--size 100G --repeat -1 \
				--on-off $onoff -n $n --time 1000 \
				--tenant 2 > ~/vimal/exports/${n}to1_${proto}_${onoff}_tenant

			exptdir=$dir/$proto-mtu$mtu-$onoff-n$n-with$iso-tcptest$tcptest-rrsize$rrsize
			$basecmd --dir $exptdir \
				$iso \
				--traffic ~/vimal/exports/${n}to1_${proto}_${onoff}_tenant \
				--mtu $mtu \
				--wtcp 2 \
				--tcptest $tcptest \
				--rrsize $rrsize

			awk 'NR == 12 { print $5 }' $exptdir/l2/netperf_rr.txt > $exptdir/mean_latency_us.txt
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
done
done

echo `date` $dir
