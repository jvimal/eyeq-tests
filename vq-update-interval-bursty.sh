
exptid=`date +%b%d-%H:%M`
dir=/tmp/$exptid/vq-bursty
time=120
mtus="9000"

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

basecmd="python tests/scenario.py --time $time --run tcpvsudp"

# Sweep for VQ update interval
for vqu in 10 25 50 100 500 1000 10000 100000 1000000; do
for mtu in $mtus; do
	subdir=mtu$mtu-vq${vqu}us
	$basecmd -n 2 --vqupdate $vqu --dir $dir/$subdir --enable \
		--traffic ~/vimal/exports/loadfiles/tmp2 \
		--mtu $mtu \
		--exptid $exptid
done
done

# Now sweep for AI/MD parameters
for aimd_dt_us in 100 500 1000 5000 10000 100000 1000000; do
for mtu in $mtus; do
	subdir=mtu$mtu-aimd-${aimd_dt_us}us
	$basecmd -n 2 --dir $dir/$subdir --enable \
		--traffic ~/vimal/exports/loadfiles/tmp2 \
		--mtu $mtu --aimd_dt_us $aimd_dt_us \
		--exptid $exptid
done
done

# Plot all the graphs
pushd ../exptdata/$exptid
mkdir graphs

for dir in *; do
    for ext in eps png pdf; do
        mkdir -p graphs/$ext
        python2.6 ~/iso/tests/plots/plot_tenant_rate.py -f $dir/l1/tenant.txt \
            -l tcp udp --accum 200 --rx --every 10 -o graphs/$ext/$dir.$ext --title '';
    done
done
echo `date` $dir

