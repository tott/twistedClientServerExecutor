#!/usr/bin/env python
"""
Very basic client that searches for a server in the same /24 network range
and connects to it. It then would execute all whitelisted commands it receives from the server.
"""

from twisted.internet import reactor, protocol, defer
import time
from socket import *
import fcntl
import sys
import ast
import signal

my_ip = None
command_whitelist = None
my_processes = []


def get_ip_address():
    iflist = open("/proc/net/dev").readlines()
    dummy_sock = socket(AF_INET, SOCK_STREAM)
    ip_addresses = {}
    for line in iflist:
        if ':' not in line:
            continue
        ifname = line.split(':')[0].strip()
        ifr = ifname + '\0' * (32 - len(ifname))
        try:
            requ = fcntl.ioctl(dummy_sock.fileno(),
                               0x8915,  # The magic SIOCGIFADDR
                               ifr)
        except IOError:
            print "Your loopback device may be dead."
            print "Check your system settings."

        addr = []
        for i in requ[20:24]:
            addr.append(ord(i))
        ip_addresses[ifname] = addr
    return ip_addresses


def server_is_up(addr):
    s = socket(AF_INET, SOCK_STREAM)
    s.settimeout(0.01)
    if not s.connect_ex((addr, 1025)):
        s.close()
        return 1
    else:
        s.close()


def async_check_output(args, ireactorprocess=None):
    """
    :type args: list of str
    :type ireactorprocess: :class: twisted.internet.interfaces.IReactorProcess
    :rtype: Deferred
    """
    if ireactorprocess is None:
        ireactorprocess = reactor

    pprotocol = ExecutorProcessProtocol()
    cmd = args.split(" ")[0]
    ireactorprocess.spawnProcess(pprotocol, cmd, args=args.split(" "))
    return pprotocol.d


class ExecutorProcessProtocol(protocol.ProcessProtocol):
    def connectionMade(self):
        print "Process connected"
        self.d = defer.Deferred()

    def connectionLost(self):
        print "Process connection closed"

    def outReceived(self, data):
        print data
        global executor
        for protocol in executor.protocols:
            protocol.transport.write(data)

    def errReceived(self, data):
        print data
        global executor
        for protocol in executor.protocols:
            protocol.transport.write(data)

    def processExited(self, reason):
        pass


class ExecutorClient(protocol.Protocol):
    def get_msg(self, data):
        try:
            msg = data.split(":", 2)
            msg = msg[-1]
        except:
            msg = data
        return msg.strip()

    def connectionMade(self):
        print "Connected!"
        self.factory.protocols.append(self)
        global command_whitelist
        command_whitelist = None
        self.transport.write("commands\n")

    def dataReceived(self, data):
        global command_whitelist
        msg = self.get_msg(data)
        try:
            command = command_whitelist[msg]
            print "Executing: %s" % command
            try:
                process = async_check_output(command)
                my_processes.append(process)
                self.transport.write("STATE:EXECUTING %s\n" % command)
            except IOError:
                pass

        except TypeError:
            msg = data.split(":")
            del(msg[0])
            msg = ":".join(msg).strip()
            try:
                command_whitelist = {}
                # TODO: put some encryption or other security measures in here
                command_whitelist = ast.literal_eval(msg)
                print "Got command list: %s" % command_whitelist
            except:
                command_whitelist = None
                print "Invalid command list received"
                time.sleep(1)
                command_whitelist = None
                self.transport.write("commands\n")
                pass
        except KeyError:
            if(msg == 'kill children'):
                print "Killing children"
                for process in my_processes:
                    try:
                        process.signalProcess(signal.SIGTERM)
                        del(my_processes[process])
                    except:
                        pass
                self.transport.write("STATE:KILLED CHILDREN\n")

    def connectionLost(self, reason):
        print "Connection lost!"
        self.factory.protocols.remove(self)

    def sendLine(self, line):
        self.transport.write(line)


class ExecutorFactory(protocol.ReconnectingClientFactory):
    protocol = ExecutorClient

    def __init__(self):
        self.protocols = []

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed - retrying!"
        self.resetDelay()
        self.maxDelay = 30
        try:
            protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        except:
            pass

    def clientConnectionLost(self, connector, reason):
        print "Connection lost - retrying!"
        self.resetDelay()
        self.maxDelay = 30
        try:
            protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
        except:
            pass


def main():
    result = get_ip_address()
    try:
        ip = result['eth0']
        ient = ""
        for j in ip:
            ient += str(j) + '.'
        ient = ient.rstrip('.')
        my_ip = ient
    except KeyError:
        for i in result:
            ient = ""
            for j in result[i]:
                ient += str(j) + '.'
            ient = ient.rstrip('.')
            my_ip = ient

    ip = my_ip.split(".", 3)
    del(ip[3])
    ip = ".".join(ip)
    server_ip = None

    for i in xrange(1, 255):
        check_ip = "%s.%s" % (ip, i)
        if(server_is_up(check_ip) == 1):
            print "Server IP: %s" % check_ip
            server_ip = check_ip
            break

    if(server_ip is None):
        sys.exit("Could not find a server")

    global executor
    executor = ExecutorFactory()
    reactor.connectTCP(server_ip, 1025, executor)
    reactor.run()

if __name__ == '__main__':
    main()
