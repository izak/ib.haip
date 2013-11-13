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

Now set up three fake addresses, bind them to a local network interface:

  sudo ip addr add 10.0.0.1/32 dev lo
  sudo ip addr add 10.0.0.2/32 dev lo
  sudo ip addr add 10.0.0.10/32 dev lo


To run it (unfortunately it has to run as root):
  sudo bin/haip -vv --wait=2 --route 1/10.0.0.10/10.0.0.1/eth0 \
    --route 2/10.0.0.10/10.0.0.2/ppp0

The --route options specifies a weight/local_ip/remote_ip/device for each
route. Lower weights are preferred over higher ones. The remote_ip is pinged,
using local_ip as source address. If it fails, the lowest non-failed route
takes it's place. If a lower-weighted route becomes available, that replaces
the current one again.

If you don't want to specify a local_ip, just leave it blank, that is use
--route 1//10.0.0.1/eth0 for example. The local_ip is there to allow you to
make use of source routing.
