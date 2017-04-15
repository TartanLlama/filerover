"""Contains methods for finding active servers

Based off code from http://stackoverflow.com/questions/603852/multicast-in-python

Usage:
Simply import the module and use its methods directly. Make sure you call setUp before calling discover for the first time"""

import socket
import struct
import select
import time

SEARCH_TIME = 100 #ms to check for servers

def setUp():
    """
    Set up the socket needed to discover servers

    Do NOT call the discover method for the first time before this one
    """

    global sock, set_up
    
    MCAST_GRP = '224.1.1.1' #multicast group
    MCAST_PORT = 40042 #my personal port

    #creates a socket with the INet address family of type datagram using UDP as the protocol
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    #set the socket to reuse INet addresses
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    #bind the socket to the correct port
    sock.bind(('', MCAST_PORT))

    #creates a string holding the IP of the multicast group and the constant for specifying to use any network interface
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)

    #subscribes the socket as interested in the multicast group
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    sock.setblocking(0)

    set_up = True

def discover():
    """
    Returns a list of IPs which are broadcasting

    You should DEFINITELY run the setUp method before running this for the first time
    """

    global sock, set_up
    
    #sets up if not already set up
    #this is essentially an exception handler, call the setUp() method manually for readability
    if not set_up:
        setUp()

    servips = [] #will hold the server IP addresses
    start_time = time.time() * 1000

    cont = True

    #finds ips which are transmitting heartbeats and adds them to a list
    while cont:
        #don't stop if there is a read failure as this is nearly inevitable
        try:
            #only need to recieve 15 bytes as that is the maximum for an IPv4 address
            ip = sock.recv(15)

            #only add the ip if it has not been found already
            if not ip in servips:
                servips.append(ip)

        except socket.error:
            pass
        
        #if the serch time has elapsed, stop
        if time.time()*1000 > start_time + SEARCH_TIME:
            cont = False
        

    return servips

#test stuff
if __name__ == '__main__':

    print 'setting up'
    setUp()
    print 'discovering'
    print discover()
