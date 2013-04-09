#!/usr/bin/env python
"""
Simple server that forwards received messages to all connected clients.
"""

from twisted.internet import reactor, protocol
from twisted.protocols import basic
import re

command_whitelist = {
    'uptime': 'uptime',
    'w': 'w',
    'ps': 'ps ef',
    'df': 'df',
    'ifconfig': '/sbin/ifconfig',
    'uname': 'uname -a',
    'bonnie++': '/usr/sbin/bonnie++ -d /home/testsuite -u testsuite -f -n 1',
    'pts/apache-1.5.2': '/usr/bin/phoronix-test-suite batch-run pts/apache-1.5.2',
    'pts/compilebench-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/compilebench-1.0.0',
    'pts/compress-gzip-1.1.0': '/usr/bin/phoronix-test-suite batch-run pts/compress-gzip-1.1.0',
    'pts/dbench-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/dbench-1.0.0',
    'pts/fio-1.2.0': '/usr/bin/phoronix-test-suite batch-run pts/fio-1.2.0',
    'pts/fs-mark-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/fs-mark-1.0.0',
    'pts/iozone-1.8.0': '/usr/bin/phoronix-test-suite batch-run pts/iozone-1.8.0',
    'pts/pgbench-1.4.0': '/usr/bin/phoronix-test-suite batch-run pts/pgbench-1.4.0',
    'pts/postmark-1.1.0': '/usr/bin/phoronix-test-suite batch-run pts/postmark-1.1.0',
    'pts/sqlite-1.8.0': '/usr/bin/phoronix-test-suite batch-run pts/sqlite-1.8.0',
    'pts/tiobench-1.1.0': '/usr/bin/phoronix-test-suite batch-run pts/tiobench-1.1.0',
    'pts/unpack-linux-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/unpack-linux-1.0.0',
}


class PubProtocol(basic.LineReceiver):
    def __init__(self, factory):
        self.factory = factory
        self.delimiter = "\n"
        self.limit_regex = re.compile('''limit\s(?P<limit>[0-9]+)''')
        self.limit = None

    def connectionMade(self):
        print "Client connected: {}".format(self.transport.getPeer().host)
        self.factory.clients.add(self)
        self.host = self.transport.getPeer().host

    def connectionLost(self, reason):
        print "Client lost!"
        self.factory.clients.remove(self)

    def lineReceived(self, line):
        print "{}: {}".format(self.transport.getPeer().host, line)
        if(line.strip() == 'commands'):
            self.commands()
        elif(line.strip() == 'help'):
            self.help()
        elif(line.strip() == 'clients'):
            self.clients()
        elif(line.strip() == 'quit'):
            self.quit()
        elif(self.limit_regex.match(line.strip())):
            self.setLimit(line.strip())
        else:
            clients_done = 0
            if(self.limit is not None):
                self.sendLine("Sending command to {} clients".format(self.limit))
            for c in self.factory.clients:
                if(self.limit is None or clients_done < self.limit):
                    c.sendLine("{}: {}".format(self.transport.getPeer().host, line))
                    if(c.host != self.host):
                        clients_done = clients_done + 1

    def help(self):
        self.sendLine("{}: help - This help".format(self.transport.getHost().host))
        self.sendLine("{}: kill children - kill all running child processes".format(self.transport.getHost().host))
        self.sendLine("{}: commands - dictionary with possible commands".format(self.transport.getHost().host))
        self.sendLine("{}: clients - get a list of connected clients".format(self.transport.getHost().host))
        self.sendLine("{}: quit - close connection".format(self.transport.getHost().host))
        self.sendLine("{}: limit <num> - limit to <num> servers".format(self.transport.getHost().host))

        for command in sorted(command_whitelist.iterkeys()):
            self.sendLine("{}: {} - {}".format(self.transport.getHost().host, command, command_whitelist[command]))

    def setLimit(self, line):
        match = self.limit_regex.match(line)
        if match:
            line_dict = match.groupdict()
            self.limit = int(line_dict['limit'])
            return True
        else:
            return False

    def commands(self):
        self.sendLine("{}: {}".format(self.transport.getHost().host, command_whitelist))

    def message(self, message):
        self.transport.write(message + '\n')

    def clients(self):
        for c in self.factory.clients:
            self.sendLine("{}: {}".format(self.transport.getPeer().host, c.host))
        self.sendLine("{}: {} clients connected".format(self.transport.getPeer().host, len(self.factory.clients)))

    def quit(self):
        self.transport.loseConnection()


class PubFactory(protocol.Factory):
    def __init__(self):
        self.clients = set()

    def buildProtocol(self, addr):
        return PubProtocol(self)

reactor.listenTCP(1025, PubFactory())
reactor.run()
