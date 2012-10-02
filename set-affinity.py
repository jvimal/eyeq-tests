import sys, os

dev = sys.argv[1]
mask = 1
count = 0

"""
CPU numbering on lancelots:

(0 4)  (Core 0, two hyperthreads)
(1 5)
(2 6)
(3 7)

So, we set TX interrupt on CPU 0
RX-0 on CPU 1
RX-1 on CPU 2
RX-2 on CPU 1
RX-3 on CPU 2
RX-4 on CPU 1
"""

mappings = [0, 1, 2, 3, 5, 6]
mappings = [0, 1, 2, 1, 2, 1]

for line in open('/proc/interrupts').xreadlines():
    if dev not in line:
        continue
    nr = line.split(':')[0]
    nr = nr.strip()

    name = line.split(' ')[-1].strip()
    mask = 1 << mappings[count]
    cmd = 'echo %x > /proc/irq/%s/smp_affinity' % (mask, nr)
    print name, cmd
    os.system(cmd)
    count += 1

