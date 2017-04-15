"""A module containing a class for broadcasting heartbeat messages using multicast

Based off code from http://stackoverflow.com/questions/603852/multicast-in-python

Usage:
This module should be imported and an instance of MulticastThread created.

You should then call start() on the thread instance to start the thread
"""

import socket
import time
import threading

class MulticastThread (threading.Thread):
    """Broadcasts heartbeat messages when started"""

    def run (self):
        global running

        MCAST_GRP = '224.1.1.1' #the multicast group
        MCAST_PORT = 40042 #my port
        INTERVAL = 50 #the time in ms between messages

        running = True

        #creates a socket with the INet address family of type datagram using UDP as the protocol
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        #limits datagram lifespan
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        #gets host IP
        host = socket.gethostbyname(socket.gethostname())
        
        #keep sending heartbeat messages
        while running:
            #send the host IP to the multicast group
            sock.sendto(host, (MCAST_GRP, MCAST_PORT))
            time.sleep(0.05) #wait for 0.05 seconds until sending the next message

        sock.close()

    def stop(self):
        """Stops the thread from running, also closing up sockets and suchlike"""
        global running
        
        running = False
