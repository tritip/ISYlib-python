
"""
	Ugly...

	work in progress, ment as proof of concept

	needs rewrite or cleanup
"""

import time

import sys
import os
import traceback
# import re
import socket
import select

import xml.etree.ElementTree as ET

from IsyEventData import event_ctrl

try:
    import fcntl
except ImportError:
    fcntl = None

__all__ = ['ISYEvent']

class ISYEvent(object) :

    def __init__(self, addr=None,  **kwargs):
	print  "ISYEvent ", self.__class__.__name__

	update_node_data = kwargs.get("update_node_data", 0)
	myisy = kwargs.get("myisy", 0)

	if  update_node_data and myisy != None :
	    self.update_node_loop(myisy)
	    return

	self.process_func = kwargs.get("process_func", None)
	self.process_func_arg = kwargs.get("process_func_arg", None)

	if self.process_func :
	    assert callable(self.process_func), "process_func Arg must me callable"

	self.connect_list = []

	if addr :
	    connect_list.append(ISYEventConnection(addr,self))

	self.__is_shut_down = 0



    def update_node_loop(self, myisy) :

	#add  check myisy class

	self.subscribe(myisy.addr)
	self.process_func = myisy._node_update_event
	self.process_func_arg = myisy

	self.events_loop()

	

    def unsubscribe(self, addr):

	remote_ip = socket.gethostbyname( host )

	if not addr in self.connect_list :
	    warning.warn("address {0}/{1} not subscribed".format(addr, remote_ip),
		RuntimeWarning)
	    return

	isyconn = s[s.index(x)]

	isyconn.disconnect()
	del(isyconn)


    def subscribe(self, addr):

	if addr in self.connect_list :
	    warning.warn("Duplicate addr", RuntimeWarning)
	    return

	self.connect_list.append(ISYEventConnection(addr, self))

    def _process_event(self, conn_obj) :
	""" 

	    _process_event : takes XML from the events stream
		coverts to a dict and passed to process_func provided
	"""
	#print "-"

	l = conn_obj.event_rf.readline()
	if len(l) == 0 :
	    raise IOError("bad read form socket")
	    # conn_obj._opensock(self.isyaddr)
	    # conn_obj._subscribe()
	# print "_process_event = ", l
	if ( l[:5] != 'POST ' ) :
	    print "Stream Sync Error"
	    for x in range(10) :
		print x, " ",
		l = conn_obj.event_rf.readline()
		if ( l[:5] == 'POST ' ) :
		    print 
		    break
	    else :
		raise IOError("can not resync event stream")

	while 1 :
	    l = conn_obj.event_rf.readline()
	    if len(l) == 2 :
		break
	    # print "HEADER : ", l
	    if l[:15].upper() == "CONTENT-LENGTH:" :
		l.rstrip('\r\n')
		data_len = int(l.split(':')[1])

	# print "HEADER data_len ", data_len

	# data = conn_obj.event_rf.readread(data_len)
	data_remaining = data_len
	L = []
	while data_remaining :
	    chunk = conn_obj.event_rf.read(data_remaining)     
	    if not chunk :
		break;
	    L.append(chunk)
	    data_remaining -= len(chunk)
	data = ''.join(L)

	ddat = dict ( )
	ev = ET.fromstring(data)
	#print "_process_event ", data,"\n\n"


	for e in list(ev) :
	    n = list(e)
	    if  n  :
		cdict = dict ()
		for child in n:
		    cdict[child.tag] = child.text
		ddat[e.tag] = cdict
	    else :
		ddat[e.tag] = e.text
	    if e.attrib :
		for k, v in e.attrib.iteritems() :
		    ddat[e.tag + "-" + k] = v
	for k, v in ev.attrib.iteritems() :
	    ddat[ev.tag + "-" + k] = v


	# print ddat
	#if ddat[control][0] == "_" :
	#	return
	# print ddat
	return(ddat,data)

    @staticmethod
    def print_event(ddat,data,arg):

	ectrl = event_ctrl.get(ddat["control"], ddat["control"])

	node = ddat["node"]

#	    if isinstance(ddat["eventInfo"], str) :
#		evi = unicode(ddat["eventInfo"],'utf-8','ignore') 
#	    else :
#		if ddat["control"] == "_1" :
#		    if "id" in ddat["eventInfo"] :
#			node = ddat["id"]
#		    if "s" in ddat["eventInfo"] :
#			evi = ddat["s"]
#		else :

	try:
	    evi = ddat["eventInfo"]
	    ti = time.strftime('%X')
	    # print ddat["Event-sid"]
	    print "%-7s %-4s\t%-22s\t%-12s\t%s\t%s" % \
		(ti, ddat["Event-seqnum"], ectrl, node, ddat["action"], evi )

	    #print ddat
	    # print data
	except :
	    print "Unexpected error:", sys.exc_info()[0]
	    print ddat
	    print data
	finally:
	    pass



    def event_iter(self, ignorelist=None, poll_interval=0.5) :
	"""Loop thought events

	    reads events packets and passes them to processor

	""" 

	for s in self.connect_list:
	    s.connect()

	while not self.__is_shut_down  :
	    try:
		r, w, e = select.select(self.connect_list, [], [], poll_interval)
		for rl in r :
		    d, x = self._process_event(rl)
		    if ignorelist :
			if d["control"] in ignorelist :
			    continue
		    yield d
	    except socket.error :
		print "socket error({0}): {1}".format(e.errno, e.strerror)
		self.reconnect()
	    except IOError as e:
		print "I/O error({0}): {1}".format(e.errno, e.strerror)
		self.reconnect()
	    except KeyboardInterrupt :
		return
	    #except :
		print "Unexpected Error:", sys.exc_info()[0]
		#traceback.print_stack()
		#print repr(traceback.extract_stack())
		#print repr(traceback.format_stack())
	    finally:
		pass

    def events_loop(self, poll_interval=0.5) :
	"""Loop thought events

	    reads events packets and passes them to processor

	""" 

	for s in self.connect_list:
	    s.connect()

	while not self.__is_shut_down  :
	    try:
		r, w, e = select.select(self.connect_list, [], [], poll_interval)
		for rs in r :
		    x, y = self._process_event(rs)
		    self.process_func(x ,y, self.process_func_arg)
	    except socket.error :
		print "socket error({0}): {1}".format(e.errno, e.strerror)
		self.reconnect()
	    except IOError as e:
		print "I/O error({0}): {1}".format(e.errno, e.strerror)
		self.reconnect()
#	    except :
#		print "Unexpected error:", sys.exc_info()[0]
	    finally:
		pass

class ISYEventConnection(object):

    def __init__(self, addr, isyevent) :
	self.event_rf = None
	self.event_wf = None
	self.event_sock = None
	self.isyaddr = addr
	self.parent = isyevent
	self.error = 0

    def __hash__(self):
	return str.__hash__(self.isyaddr)

    def __str__(self):
	return self.isyaddr

#    def __del__(self):
#	pass

    def __eq__(self,other):
	if isinstance(other, str) :
	    return self.isyaddr == other
	if not hasattr(other, "isyaddr") :
	    return object.__eq__(self,other)
	return self.isyaddr == other.isyaddr

    def fileno(self): 
	""" Interface required by select().  """ 
	return self.event_sock.fileno() 

    def reconnect(self):
	print "--reconnect to self.isyaddr--"
	self.error += 1
	self.disconnect()
	self.connect()

    def disconnect(self):
	try :
	    if self.event_rf :
		self.event_rf.close()
		self.event_rf = False
	except :
	    pass

	try :
	    if self.event_wf :
		self.event_wf.close()
		self.event_wf = False
	except :
	    pass

	try :
	    if self.event_sock :
		self.event_sock.close()
		self.event_sock = False
	except :
	    pass

    def connect(self):
	self._opensock()
	self._subscribe()

    def _opensock(self):

	print "_opensock ", self.isyaddr

	self.event_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	server_address = (self.isyaddr, 80)
	self.event_sock.connect(server_address)

	#sn =  sock.getsockname()   
	#self.myip = sn[0]
	#print "P ", self.myip

	#self.myurl = "http://{0}:{1}/".format( sn[0], self.server_address[1] )
	#print "myurl ", self.myurl

	if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
	    flags = fcntl.fcntl(self.event_sock.fileno(), fcntl.F_GETFD)
	    flags |= fcntl.FD_CLOEXEC
	    fcntl.fcntl(self.event_sock.fileno(), fcntl.F_SETFD, flags)

	self.event_rf = self.event_sock.makefile("rb")
	self.event_wf = self.event_sock.makefile("wb")

	return self.event_sock;

    def _subscribe(self):

	print "_subscribe : "
	# <ns0:Unsubscribe><SID>uuid:168</SID><flag></flag></ns0:Unsubscribe>
	post_body = "<s:Envelope><s:Body>" \
	    "<u:Subscribe xmlns:u=\"urn:udicom:service:X_Insteon_Lighting_Service:1\">" \
	    + "<reportURL>REUSE_SOCKET</reportURL>" \
	    + "<duration>infinite</duration>" \
	    "</u:Subscribe></s:Body></s:Envelope>" 
	    # "\r\n\r\n" 

	post_head = "POST /services HTTP/1.1\r\n" \
	    + "Host: {0}:80\r\n".format(self.isyaddr) \
	    + "Authorization: Basic YWRtaW46YWRtaW4=\r\n" \
	    + "Content-Length: {0}\r\n".format( len(post_body) ) \
	    + "Content-Type: text/xml; charset=\"utf-8\"\r\n" \
	    + "\r\n\r\n"

	post = post_head + post_body

	print post

	msglen = len(post)
	totalsent = 0

	self.event_wf.write(post)
	self.event_wf.flush()

	l = self.event_rf.readline()
	if ( l[:5] != 'HTTP/' ) :
	    raise ValueError( l )

	l.split(' ', 1)[1]
	if ( l.split(' ')[1] != "200") :
	    raise ValueError( l )

	while 1 :
	    l = self.event_rf.readline()
	    if len(l) == 2 :
		break
	    if l[:15] == "Content-Length:" :
		l.rstrip('\r\n')
		data_len = int(l.split(':')[1])


	reply = self.event_rf.read(data_len) 
	print "_subscribe reply = '", reply, "'"


#
# Do nothing
# (syntax check)
#
if __name__ == "__main__":
    import __main__
    print __main__.__file__

    print("syntax ok")
    exit(0)