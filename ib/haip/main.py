import os
import socket
import fcntl
import struct
import logging
import traceback
from time import sleep
import shlex
from argparse import ArgumentParser
from ib.haip import ping as pingmodule
from ib.haip.util import sh

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

def run():
    parser = ArgumentParser()
    parser.add_argument('--logfile', help="The filename to log to")
    parser.add_argument('--iptools', default='/sbin/ip',
        help="Location of iptools binary")
    parser.add_argument('--ping', default='/bin/ping',
        help="Location of ping binary")
    parser.add_argument('--verbose', '-v', action='count',
        help="Increase verbosity", default=0)
    parser.add_argument('--route', action='append',
        help="Route info in format weight/destination_ip/net_device:[gw-ip]")
    parser.add_argument('--fail', default=3, type=int,
        help="Number of times a ping fails before we switch over")
    parser.add_argument('--wait',
        default=10, type=int, help="Seconds to wait between pings")
    parser.add_argument('--toggle',
        help="Executable to call each time after the gateway was toggled")

    options = parser.parse_args()

    # Configure logging
    if options.logfile:
        logging.basicConfig(level=max(4-options.verbose,1)*10,
            format='%(asctime)s %(levelname)s %(message)s',
            filename=options.logfile)
    else:
        logging.basicConfig(level=max(4-options.verbose,1)*10,
            format='%(asctime)s %(levelname)s %(message)s')

    # Configure ping module
    pingmodule.PING = options.ping

    logging.info("Starting haip")
    failcounters = {}

    routes = [tuple(x.split('/')) for x in options.route]
    activeroute = None

    try:
        while True:
            # Ping the various routes
            for route in routes:
                if len(route) > 3:
                    weight, dst, dev, src = route
                    dev = dev.split(':')[0]
                else:
                    weight, dst, dev = route
                    dev = dev.split(':')[0]

                    # Determine src ip
                    try:
                        src = get_ip_address(dev)
                    except IOError:
                        failcounters[route] = min(failcounters.get(route, 0), options.fail) + 1
                        logging.error('Cannot find ip for device %s', dev)
                        continue

                logging.info("Pinging %s from %s" % (dst, src))
                try:
                    if pingmodule.ping(dst, src_addr=src):
                        failcounters[route] = 0
                        logging.info("success, resetting failcount")
                    else:
                        failcounters[route] = min(failcounters.get(route, 0), options.fail) + 1
                        logging.info("fail, incrementing failcount to %d",
                            failcounters[route])
                except KeyboardInterrupt:
                    raise
                except:
                    logging.error("An exception occurred.")
                    logging.error(traceback.format_exc())
                    
            # Sort routes by whether they are failed, and weight
            alternatives = failcounters.items()
            alternatives.sort(key=lambda x: (x[1]>=options.fail, x[0][0]))

            # Only switch if lowest fail count is in fact low enough and
            # it isn't already active
            if alternatives and alternatives[0][1] < options.fail and \
                    activeroute != alternatives[0][0]:

                activeroute = alternatives[0][0]
                dev = activeroute[2]
                logging.warn("Switching gateway to %s" % dev)

                # Call ip route replace default dev $gw
                dev = dev.split(':')
                cmd = [options.iptools, 'route', 'replace', 'default']
                if len(dev) > 1:
                    cmd.extend(['via', dev[1]])
                cmd.extend(['dev', dev[0]])
                sh(cmd)

                # Call the toggle command
                if options.toggle is not None:
                    env = {
                        'IPTOOLS': options.iptools,
                        'IFNAME': dev[0],
                        'GATEWAY': len(dev) > 1 and dev[1] or '',
                    }
                    env.update(os.environ)
                    sh(shlex.split(options.toggle), env=env)

            sleep(options.wait)
    except KeyboardInterrupt:
        pass
