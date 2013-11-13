import logging
import traceback
from time import sleep
from argparse import ArgumentParser
from ib.haip.ping import ping

def run():
    parser = ArgumentParser()
    parser.add_argument('--logfile', help="The filename to log to")
    parser.add_argument('--iptools', default='/sbin/ip',
        help="Location of iptools binary")
    parser.add_argument('--verbose', '-v', action='count',
        help="Increase verbosity", default=0)
    parser.add_argument('--route', action='append',
        help="Route info in format weight/source_ip/destination_ip/gw_ip")
    parser.add_argument('--fail', default=3, type=int,
        help="Number of times a ping fails before we switch over")
    parser.add_argument('--wait',
        default=10, type=int, help="Seconds to wait between pings")

    options = parser.parse_args()

    # Configure logging
    if options.logfile:
        logging.basicConfig(level=max(4-options.verbose,1)*10,
            format='%(asctime)s %(levelname)s %(message)s',
            filename=options.logfile)
    else:
        logging.basicConfig(level=max(4-options.verbose,1)*10,
            format='%(asctime)s %(levelname)s %(message)s')

    logging.info("Starting haip")
    failcounters = {}

    routes = [x.split('/') for x in options.route]
    activeroute = None

    try:
        while True:
            # Ping the various routes
            for route in routes:
                route = tuple(route)
                weight, src, dst, gw = route
                logging.info("Pinging %s from %s" % (dst, src))
                try:
                    if ping(dst, src_addr=src):
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
                gw = activeroute[3]
                logging.warn("Switching gateway to %s" % gw)
                # TODO: Add command here that switches it. Use subprocess
                # module to call:
                # ip route replace default dev $gw

            sleep(options.wait)
    except KeyboardInterrupt:
        pass
