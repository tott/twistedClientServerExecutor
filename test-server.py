#!/usr/bin/env python
"""
Simple server that forwards received messages to all connected clients.
"""

from twisted.internet import reactor, protocol
from twisted.protocols import basic

command_whitelist = {
    'uptime': 'uptime',
    'w': 'w',
    'ps': 'ps ef',
    'df': 'df',
    'ifconfig': 'ifconfig',
    'uname': 'uname -a',
    'bonnie++': '/usr/sbin/bonnie++ -d /home/testsuite -u testsuite -f -n 1',
    'phoronix pts/apache-1.5.2': '/usr/bin/phoronix-test-suite batch-run pts/apache-1.5.2',
    'phoronix pts/blake2-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/blake2-1.0.0',
    'phoronix pts/blogbench-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/blogbench-1.0.0',
    'phoronix pts/bork-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/bork-1.0.0',
    'phoronix pts/botan-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/botan-1.0.0',
    'phoronix pts/build-imagemagick-1.6.0': '/usr/bin/phoronix-test-suite batch-run pts/build-imagemagick-1.6.0',
    'phoronix pts/build-linux-kernel-1.3.0': '/usr/bin/phoronix-test-suite batch-run pts/build-linux-kernel-1.3.0',
    'phoronix pts/build-mplayer-1.3.0': '/usr/bin/phoronix-test-suite batch-run pts/build-mplayer-1.3.0',
    'phoronix pts/build-php-1.3.1': '/usr/bin/phoronix-test-suite batch-run pts/build-php-1.3.1',
    'phoronix pts/bullet-1.2.0': '/usr/bin/phoronix-test-suite batch-run pts/bullet-1.2.0',
    'phoronix pts/byte-1.2.0': '/usr/bin/phoronix-test-suite batch-run pts/byte-1.2.0',
    'phoronix pts/cachebench-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/cachebench-1.0.0',
    'phoronix pts/clomp-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/clomp-1.0.0',
    'phoronix pts/compilebench-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/compilebench-1.0.0',
    'phoronix pts/compress-7zip-1.6.0': '/usr/bin/phoronix-test-suite batch-run pts/compress-7zip-1.6.0',
    'phoronix pts/compress-gzip-1.1.0': '/usr/bin/phoronix-test-suite batch-run pts/compress-gzip-1.1.0',
    'phoronix pts/compress-lzma-1.2.0': '/usr/bin/phoronix-test-suite batch-run pts/compress-lzma-1.2.0',
    'phoronix pts/compress-pbzip2-1.4.0': '/usr/bin/phoronix-test-suite batch-run pts/compress-pbzip2-1.4.0',
    'phoronix pts/crafty-1.3.0': '/usr/bin/phoronix-test-suite batch-run pts/crafty-1.3.0',
    'phoronix pts/dbench-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/dbench-1.0.0',
    'phoronix pts/dcraw-1.1.0': '/usr/bin/phoronix-test-suite batch-run pts/dcraw-1.1.0',
    'phoronix pts/dolfyn-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/dolfyn-1.0.0',
    'phoronix pts/espeak-1.3.0': '/usr/bin/phoronix-test-suite batch-run pts/espeak-1.3.0',
    'phoronix pts/ffte-1.0.1': '/usr/bin/phoronix-test-suite batch-run pts/ffte-1.0.1',
    'phoronix pts/fio-1.2.0': '/usr/bin/phoronix-test-suite batch-run pts/fio-1.2.0',
    'phoronix pts/fs-mark-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/fs-mark-1.0.0',
    'phoronix pts/hdparm-read-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/hdparm-read-1.0.0',
    'phoronix pts/himeno-1.1.0': '/usr/bin/phoronix-test-suite batch-run pts/himeno-1.1.0',
    'phoronix pts/iozone-1.8.0': '/usr/bin/phoronix-test-suite batch-run pts/iozone-1.8.0',
    'phoronix pts/mafft-1.4.0': '/usr/bin/phoronix-test-suite batch-run pts/mafft-1.4.0',
    'phoronix pts/pgbench-1.4.0': '/usr/bin/phoronix-test-suite batch-run pts/pgbench-1.4.0',
    'phoronix pts/postmark-1.1.0': '/usr/bin/phoronix-test-suite batch-run pts/postmark-1.1.0',
    'phoronix pts/sqlite-1.8.0': '/usr/bin/phoronix-test-suite batch-run pts/sqlite-1.8.0',
    'phoronix pts/tiobench-1.1.0': '/usr/bin/phoronix-test-suite batch-run pts/tiobench-1.1.0',
    'phoronix pts/unpack-linux-1.0.0': '/usr/bin/phoronix-test-suite batch-run pts/unpack-linux-1.0.0',
}


class PubProtocol(basic.LineReceiver):
    def __init__(self, factory):
        self.factory = factory
        self.delimiter = "\n"

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
        else:
            for c in self.factory.clients:
                c.sendLine("{}: {}".format(self.transport.getPeer().host, line))

    def help(self):
        self.sendLine("{}: help - This help".format(self.transport.getHost().host))
        self.sendLine("{}: kill children - kill all running child processes".format(self.transport.getHost().host))
        self.sendLine("{}: commands - dictionary with possible commands".format(self.transport.getHost().host))
        self.sendLine("{}: clients - get a list of connected clients".format(self.transport.getHost().host))
        self.sendLine("{}: quit - close connection".format(self.transport.getHost().host))

        for command in sorted(command_whitelist.iterkeys()):
            self.sendLine("{}: {} - {}".format(self.transport.getHost().host, command, command_whitelist[command]))

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
