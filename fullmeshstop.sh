

for i in {1..20}; do
  ssh l$i "ps axo pid,comm,args | egrep 'bash.*taskset' | awk '{print \$1}' | xargs kill -9";
  ssh l$i "ps axo pid,comm,args | egrep 'iperf' | awk '{print \$1}' | xargs kill -9";
done
