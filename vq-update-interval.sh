
dir=~/vimal/10g/exptdata/`date +%b%d-%H:%M`/vq-update-interval
time=120

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

basecmd="python tests/scenario.py --time $time -n 1 --run tcpvsudp"

size=100G
proto=udp
 # WITH ISOLATION
python tests/genconfig.py --type $proto --traffic incast \
	--size $size --repeat 1000 \
	--inter 5 -n 16 --time 1000 \
	--tenant 2 > ~/vimal/exports/14to1_${size}_${proto}_tenant

for vqu in 10 25 50 100 500 1000; do
for mtu in 1500 9000; do

	$basecmd --vqupdate $vqu --dir $dir/mtu$mtu-vq${vqu}us --enable \
		--traffic ~/vimal/exports/14to1_${size}_${proto}_tenant \
		--mtu $mtu

done
done

echo `date` $dir
