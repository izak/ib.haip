This is a work in progress.

Install python and virtualenv:

  sudo apt-get install python2.7 python-virtualenv

Create a working directory, you can call it something other than z:

  virtualenv z
  cd z
  git clone https://github.com/izak/ib.haip.git
  cd ib.haip
  ../bin/python setup.py develop
  cd ..

Now set up two fake addresses, bind them to a local network interface:

  sudo ip addr add 10.0.0.1/32 dev eth0
  sudo ip addr add 10.0.0.2/32 dev eth0


To run it (unfortunately it has to run as root):
  sudo bin/haip -vv --wait=2 --route 1/10.0.0.1/eth0 \
    --route 2/10.0.0.2/eth0

To simulate a link outage, drop the first fake address to make it unpingable:

  sudo ip addr del 10.0.0.2/32 dev eth0

Switchover should occur within a few seconds with this setup. Repeat the first
command to add it back, and it should switch back again.

The --route options specifies a weight/remote_ip/device for each route. Lower
weights are preferred over higher ones. The remote_ip is pinged, using the
local ip of the device as source address. If it fails, the lowest non-failed
route takes it's place. If a lower-weighted route becomes available, that
replaces the current one again.

Using the local device ip is done so that source routing should ensure that the
ping is routed over that interface, so you can test that interface even if the
default route says otherwise.
