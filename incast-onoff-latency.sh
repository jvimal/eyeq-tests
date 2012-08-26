exptid=`date +%b%d-%H:%M`
dir=/tmp/$exptid/incast-onoff-latency
time=120
sys=CloudSwitch
sys=EyeQ

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

n=3

basecmd="python tests/scenario.py --time $time -n $n --run tcpvsudp --exptid $exptid"

for tcptest in latency; do
for rrsize in 1,1; do
for onoff in 5ms,20ms; do
for iso in "" "--enable"; do
	for proto in udp; do
		for mtu in 1500; do
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

pushd ~/vimal/10g/exptdata/$exptid
proto=udp
mtu=1500
exptdir1=$proto-mtu$mtu-$onoff-n$n-with-tcptest$tcptest-rrsize$rrsize
exptdir2=$proto-mtu$mtu-$onoff-n$n-with--enable-tcptest$tcptest-rrsize$rrsize

for edir in $exptdir1 $exptdir2; do
	awk 'NR == 12 { print $5 }' $edir/l2/netperf_rr.txt > $edir/mean_latency_us.txt
done

for ext in png pdf; do
	python ~/iso/tests/plots/plot-rr-latency.py \
		--rr $exptdir2/l2/netperf_rr.txt $exptdir1/l2/netperf_rr.txt \
		--xlim 0,1000 \
		--ymin 0.5 \
		-o latency-$rrsize.$ext \
		--legend "with $sys" "without $sys"
done

popd

done
done
done

echo `date` $dir
