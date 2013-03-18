# rest_client.py - Testing of Trigger/treq REST client

from __future__ import print_function
import os
import sys
import treq
from twisted.internet import reactor, defer, task
from twisted.python import log
import urlparse

LOGFILE = '/tmp/rest_client.log'
log.startLogging(open(LOGFILE, 'w'), setStdout=False)

# Trigger setup
os.environ['TRIGGER_SETTINGS'] = '/tmp/trigger_settings.py'
os.environ['NETDEVICES_SOURCE'] = '/tmp/netdevices.csv'
from trigger.conf import settings
from trigger.netdevices import NetDevices
nd = NetDevices(with_acls=False)


class RestClientError(Exception):
    """A generic REST client error"""


# TODO (jathan): Looks like I'll have to ditch treq and just roll a custom
# HTTPClientFactory that uses the Trigger error-handling semantics. Maybe.
'''
from twisted.internet.protocol import Protocol
from twisted.protocols.policies import TimeoutMixin
from twisted.web.client import ResponseDone

class BodyCollector(Protocol, TimeoutMixin):
    def __init__(self, finished, collector):
        self.finished = finished
        self.collector = collector

    def dataReceived(self, data):
        self.collector(data)

    def receiveError(self, reason, dec):
        self.sendDisconnect(reason, desc)

    def timeoutConnection(self):
        log.msg("TIMEO OUT")
        self.factory.err = RestClientErrror("TIMED OUT!!")
        self.loseConnection()

    def connectionLost(self, reason):
        if reason.check(ResponseDone):
            self.finished.callback(None)
            return None

        self.finished.errback(reason)
'''

class RestClient(object):
    def __init__(self, url=None, username=None, password=None, auth=None,
                 api_key=None, with_errors=False, command_interval=0):
        self.url = url
        self.username = username
        self.password = password
        self.auth = auth or (username, password)
        self.api_key = api_key
        self.command_interval = command_interval
        self.with_errors = with_errors
        self.commands = []
        self.results = []
        self.errors = []
        self.protocol = None
        self.store_results = False

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.url)

    @property
    def auth(self):
        return self.__auth

    @auth.setter
    def auth(self, value):
        if isinstance(value, basestring):
            raise AttributeError("`auth` cannot be a string.")

        t_auth = tuple(value) if value is not None else value

        if t_auth is not None:
            if len(t_auth) != 2:
                raise AttributeError("`auth` must have 2 items. Invalid value: %r" % (value,))
            if not all(t_auth):
                t_auth = None

        self.__auth = t_auth

    def data_received(self, bytes):
        self.data += bytes
        log.msg('[%s] BYTES: %r' % (self.url, bytes))
        return bytes

    @staticmethod
    def has_http_error(code):
        """If code not ok, it's an error!"""
        ok = (200,)
        return code not in ok

    def make_request(self, path, method='GET', auth=None, data=None,
                     store_results=None, **kwargs):
        """Make an http request. Returns a deferred."""
        log.msg('Fetching URL path: %s' % path)
        if auth is None:
            auth = self.auth
        if store_results is None:
            store_results = self.store_results

        #self.data = '' # for streaming results, not used yet.

        # Craft the URL and store the "commands" executed
        url = urlparse.urljoin(self.url, path)
        self.commands.append(url)

        # Select and call our HTTP method
        func = getattr(treq, method.lower())
        d = func(url, auth=auth, data=data, **kwargs)
        
        # Handle streaming responses. I don't think we'll need this right now
        # but if it comes to a point where we write our own HTTP Client
        # protocol and leverage dataReceived() we may bring this back.
        #d.addCallback(treq.collect, self.data_received)

        # Handle basic responses
        d.addCallbacks(self.handle_response, self.handle_failure)

        # Store the result in self.results
        if store_results:
            d.addCallback(self.store_result)

        return d

    @defer.deferredGenerator
    def multi_request(self, commands, **kwargs):
        """Perform multiple requests in series and return their results."""
        log.msg('COMMANDS:', commands)
        for command in iter(commands):

            # Wait for a deferred object to come from self.make_request
            wfd = defer.waitForDeferred(self.make_request(command,
                                                          store_results=True, **kwargs))
            yield wfd

            # Get the value and send it along. :)
            result = wfd.getResult()
            yield result

        yield self.results

    def handle_response(self, response, *args, **kwargs):
        log.msg('got response:', response)

        # Only raise exceptions if with_errors isn't set
        if self.has_http_error(response.code) and not self.with_errors:
            raise RestClientError('%s %s' % (response.code, response.phrase))

        result = treq.text_content(response)
        return result

    def handle_failure(self, failure, *args, **kwargs):
        """Handle errors here"""
        log.msg('GOT FAILURE', failure)
        self.errors.append(failure)
        if not self.with_errors:
            return failure

    def store_result(self, result):
        """Store the result!"""
        self.results.append(result)

def stop_reactor(result):
    reactor.stop()
    return result

def execute_rest(device, commands, creds=None, with_errors=False):
    if creds is None:
        creds = ('jathan', 'jathan')
    client = RestClient('http://' + device.nodeName, auth=creds,
                        with_errors=with_errors)
    d = client.multi_request(commands)
    return d

if __name__ == '__main__':

    dev = nd.find('httpbin.org')
    dev.dump()

    commands = ['/ass', '/ip', '/get', '/headers', '/gzip', '/status/401']
    d = execute_rest(dev, commands, with_errors=True)
    #d = execute_rest(dev, commands, with_errors=False)

    # Direct client usage
    '''
    url = 'http://httpbin.org/'
    r = RestClient(url)
    d = r.make_request('ip')
    #d = r.request('basic-auth/jathan/jathan', auth=('jathan', 'jathan'))
    '''

    d.addBoth(stop_reactor)
    reactor.run()
