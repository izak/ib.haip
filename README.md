What is it
==========

This is a simple python program that watches two or more network interfaces
and ensurs that the default route points to an interface that is up.

To develop
----------

* Install python and virtualenv:

        sudo apt-get install python2.7 python-virtualenv

* Create a working directory, you can call it something other than z:

        virtualenv z
        cd z
        git clone https://github.com/izak/ib.haip.git
        cd ib.haip
        ../bin/python setup.py develop
        cd ..

* Now set up two fake addresses,  and bind them to a local network interface:

        sudo ip addr add 10.0.0.1/32 dev eth0
        sudo ip addr add 10.0.0.2/32 dev eth0


* To run it (unfortunately it has to run as root):
        sudo bin/haip -vv --wait=2 --route 1/10.0.0.1/eth0 \
          --route 2/10.0.0.2/eth0

* To simulate a link outage, drop the first fake address to make it unpingable:

        sudo ip addr del 10.0.0.1/32 dev eth0

* Switchover should occur within a few seconds with this setup. Repeat the first
  command to add it back, and it should switch back again.

The --route options specifies a weight/remote-p/device for each route. Lower
weights are preferred over higher ones. The remote-ip is pinged, using the
local ip of the device as source address. If it fails, the lowest non-failed
route takes it's place. If a lower-weighted route becomes available, that
replaces the current one again.

When you are done, use the del command above to remove both ip addresses again.

Simple example
-------------

In this example we will setup an ethernet link with a backup ppp link. I will
assume that you alreadt have the ethernet link working. It is okay to
leave the default gateway configuration for the ethernet interface in place,
because ppp0 is the backup interface and the monitoring script will
replace the route as needed.

The first thing you need to do is add two routing tables. Edit
`/etc/iproute2/rt_tables` and add these at the bottom:

    10 T1
    20 T2

Next configure your ethernet interface to add a routing table. For this example
I will assume that a private /24 network behind an ADSL router is used, that
the gateway is `192.168.8.1` and the host itself is `192.168.8.50`:

    iface eth0 inet static
        address 192.168.8.50
        netmask 255.255.255.0
        gateway 192.168.8.1
        up /sbin/ip route add 192.168.8.0/24 dev eth0 src 192.168.8.50 table T1
        up /sbin/ip route add default via 192.168.8.1 table T1
        up /sbin/ip rule add from 192.168.8.50 table T1
        down /sbin/ip rule del from 192.168.8.50 lookup T1
        down /sbin/ip route flush table T1

To configure a ppp link, start be editing `/etc/chatscripts/provider`:

    ABORT BUSY ABORT 'NO CARRIER' ABORT VOICE ABORT 'NO DIALTONE' ABORT 'NO DIAL TONE' ABORT 'NO ANSWER' ABORT DELAYED
    '' ATZ
    OK AT+CGDCONT=1,"IP","internet"
    OK "ATDT *99***1#"
    CONNECT \d\c

Configure `/etc/ppp/peers/provider`

    hide-password
    noauth
    connect "/usr/sbin/chat -v -f /etc/chatscripts/provider"
    debug
    /dev/ttyACM1
    115200
    noipdefault
    user "internet"
    remotename provider
    ipparam provider

Notice that `defaultroute` and `userpeerdns` is explicitly disabled here. You
should configure a DNS solution, the easiest of which is to use an open dns
server.

Edit `/etc/ppp/pap-secrets` and add:

    "internet" provider "p"

Depending on your provider, you may have to edit `/etc/ppp/chap-secrets`
instead.

Now add a file `/etc/ppp/ip-up.d/01routing` and make it executable:

    #!/bin/sh
    /sbin/ip route add $IPREMOTE dev $IFNAME src $IPLOCAL table T2
    /sbin/ip route add default via $IPREMOTE table T2
    /sbin/ip rule add from $IPLOCAL table T2

Add a file `/etc/ppp/ip-down.d/01routing` and make it executable:

    #!/bin/sh
    /sbin/ip rule del from $IPLOCAL table T2
    /sbin/ip route flush table T2

These two routing scripts ensure that table T2 is populated with an alternate
routing table that routes out via ppp0, and which is used if the source ip of
the outgoing packet is that of the ppp0 interface.

Now edit `/etc/network/interfaces` and add the ppp0 stanza:

    auto ppp0
    iface ppp0 inet ppp
        provider provider

That should ensure that ppp0 comes up at boot time. You can start it now with
this command:

    ifup ppp0

So what's with all the routing?
-------------------------------

The extra routing tables allows us to do source-routing, in other words, the
outgoing route is decided based on the source address of the outgoing
connection or packet. This allows us to bypass the default route that is
currently active and send data over either interface by simply binding to
the ip address of that interface. Look at the man page for the `ping` command
and note the `-I` option, which is meant to do precisely this.

Testing the routing
-------------------

You can test which route will be taken with this command:

    ip route get 8.8.8.8 from 192.168.8.50

This should indicate that it is using eth0. Do the same with the ip assigned to
ppp0, it should indicate that the ppp0 interface is used.

Testing failover
----------------

Finally, run this script:

        sudo bin/haip -vv --wait=2 --route 1/8.8.8.8/eth0 \
          --route 2/8.8.8.8/ppp0

This should ping the same ip (8.8.8.8, a google dns server, but replace with
whatever you want) over both interfaces, and if any link goes down it will
replace the default route with the next best one.

You can fake unreachability by adding an unreachable route and removing it
again later.

    sudo ip route add unreachable 8.8.8.8 && \
    sleep 20 && \
    sudo ip route del unreachable 8.8.8.8

TODO
====

1. It needs a good startup script, logging, and all those things. And it needs
to be turned into a debian package.
