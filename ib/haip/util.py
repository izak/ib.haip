import logging
import subprocess

class CommandFailed(Exception):
    def __init__(self, code):
        super(CommandFailed, self).__init__(self, code)
        self.code = code

def sh(command):
    logging.info('Executing command %s', ' '.join(command))
    stdout = open('/dev/null', 'w')
    stderr = subprocess.STDOUT
    try:
        p = subprocess.Popen(command,
            stdin=subprocess.PIPE, stdout=stdout, stderr=stderr)
        p.communicate(input=None)
    finally:
        stdout.close()
    if p.returncode != 0:
        raise CommandFailed(p.returncode)
