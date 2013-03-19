#!/usr/bin/env python
# -*- coding: utf-8 -*-

# a10_api.py this package is for common API task
# Source:
# http://www.a10networks.com/vadc/index.php/forums/topic/get-the-vrrp-a-status-via-snmp-or-axapi/#post-1110

import httplib
import urllib
import urllib2
import socket
import ssl
from xml.dom import minidom

class UrlBuilder(object):
    def __init__(self, domain, path, params):
        self.domain = domain
        self.path = path
        self.params = params

    def withPath(self, path):
        self.path = path
        return self

    def withParams(self,params):
        self.params = params
        return self

    def __str__(self):
        return 'https://' + self.domain + self.path + self.params
        # or return urlparse.urlunparse( ( "http", self.domain, self.path, # self.params, "", "" )

    def build(self):
        return self.__str__()

class Auth(object):
    @classmethod
    def sessionID(cls, host, username, password):
        services_path = "/services/rest/V2/"
        builder_auth_params = ''
        sid_url = UrlBuilder(host, services_path, builder_auth_params)
        method = 'authenticate'
        authparams = urllib.urlencode({
            'method': method,
            'username': username,
            'password': password
        })
        sessionID = minidom.parse(urllib2.urlopen(sid_url.__str__(), authparams)).getElementsByTagName('session_id')[0].childNodes[0].nodeValue
        return sessionID

    @classmethod
    def sessionClose(cls, host, sid):
        method = "method=session.close"
        response = Req.get(host, method, sid)
        return response

class Path(object):
    @classmethod
    def v2(cls):
        return "/services/rest/V2/"

    @classmethod
    def sessionID(cls):
        return "?session_id="

class Req(object):
    @classmethod
    def get(cls, host, method, sid):
        url = UrlBuilder(host, Path.v2(), Path.sessionID() + sid + "&" + method.__str__() + "&format=json")
        data = urllib2.urlopen(url.__str__()).read()
        return data

    @classmethod
    def post(cls, host, method, sid, config):
        #print host, method, sid, config
        #exit()
        url = UrlBuilder(host, Path.v2(), Path.sessionID() + sid + "&" + method.__str__() + "&format=json")
        #body = urllib.urlencode(config)
        #print body
        data = urllib2.urlopen(url.__str__(),config).read()
        return data

class Partition(object):
    @classmethod
    def active(cls, host, sid, name):
        data = Req.get(host, 'method=system.partition.active&name='+name, sid)
        return data

class HTTPSConnectionV3(httplib.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        httplib.HTTPSConnection.__init__(self, *args, **kwargs)
        
    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        try:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_SSLv3)
        except ssl.SSLError, e:
            print("Trying SSLv3.")
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_SSLv23)
            
class HTTPSHandlerV3(urllib2.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(HTTPSConnectionV3, req)
# install opener
urllib2.install_opener(urllib2.build_opener(HTTPSHandlerV3()))


if __name__ == '__main__':

    username = "jathan"
    import getpass
    password = getpass.getpass("Password for %s: " % username)
    host = "ax-ash-pop-1.lb.aol.com"

    '''
    Separate request by \n
    
    '''

    config = "show vrrp-a \n sh int br \n show session"
    sid = Auth.sessionID(host, username, password)
    vrrpStatus = Req.post(host, 'method=cli.show_info', sid, config)

    print vrrpStatus

    '''
    Output:
    show vrrp-a
    vrid default
    Unit State Weight Priority
    1 (Local) Active 65534 150
    vrid that is running: default
    '''
