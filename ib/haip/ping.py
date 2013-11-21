from ib.haip.util import sh, CommandFailed

PING = '/bin/ping' # Make this configurable

def ping(dest_addr, src_addr=None, timeout=2):
    cmd = [PING, '-s', '1024', '-c', '1', '-w', str(timeout)]
    if src_addr is not None:
        cmd.extend(['-I', src_addr])
    cmd.append(dest_addr)
    try:
        sh(cmd)
    except CommandFailed:
        return False
    return True
