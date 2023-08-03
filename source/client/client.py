'''
Created on 13-01-2020

@author: Panagiotis Minaidis
'''

import sys
import random
import os

from twisted.internet.defer import Deferred
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.python import log

import txthings.coap as coap
import txthings.resource as resource

from ipaddress import ip_address


class GetAgent:
    ####################################################################
    # The GetAgent attempts to retrieve the results of the offloaded 
    # execution, using the unique ID assigned to the program by the
    # server.
    #
    # If the server does not respond an error message is displayed 
    # and execution stops.
    #
    # If the server responds with the results, then they are displayed
    # and execution stops.
    #
    # If the server responds with a "Not available" message, the server
    # waits { delay / [2**k] } seconds before trying again, where
    # k is the number of the "get result" requests already made to the 
    # server and delay is the original prediction of the mean waiting 
    # time. If the Agent ends up waiting more than 1.75 * delay seconds, 
    # then the Agent aborts waiting for execution on the server and
    # runs the code locally.
    #################################################################### 
    def __init__(self, protocol, pload):
        global delay
        self.protocol = protocol
        self.pload = pload
        self.wt = 0
        self.prediction = delay
        reactor.callLater(0, self.requestResource)

    def requestResource(self):
        request = coap.Message(code=coap.GET, payload=self.pload)
        request.opt.uri_path = (b'serve',)
        request.opt.observe = 0
        request.remote = (ip_address("192.168.1.185"), coap.COAP_PORT)
        d = protocol.request(request)
        d.addCallback(self.printResponse)
        d.addErrback(self.noResponse)

    def printResponse(self, response):
        global delay
        if response.payload == "Not available.":
            if (self.prediction / delay) > 4:
                print("Server takes too long, running locally.")
                os.system("gcc load.c -o load")
                os.system("./load "+str(EXECUTION_TIME))
                reactor.stop()
            else:
                reactor.callLater(delay, self.requestResource)
                delay = delay / 2
        else:
            print("Result is: "+response.payload)
            reactor.stop()

    def noResponse(self, failure):
        print('Failed to fetch resource for GetAgent:')
        print(failure)
        reactor.stop()


class SubmitAgent(): 
    ###################################################################
    # The SubmitAgent transmits the source code of the offloaded 
    # program to the server.
    #
    # If the server does not respond an error message is displayed 
    # and execution stops.
    #
    # Otherwise, the server responds with a unique ID. This ID is
    # passed to a GetAgent, which uses it to periodically request the 
    # output of the submitted program from the server.
    ###################################################################  

    def __init__(self, protocol):
        self.protocol = protocol
        reactor.callLater(0, self.putResource)

    def putResource(self):
        with open('load.c', 'r') as file:
            payload = file.read()
        request = coap.Message(code=coap.PUT, payload="Input = "+str(ACCELERATED_TIME)+"\n"+payload)
        request.opt.uri_path = (b'serve',)
        request.opt.content_format = coap.media_types_rev['text/plain']
        request.remote = (ip_address('192.168.1.185'), coap.COAP_PORT)
        d = protocol.request(request)
        d.addCallback(self.getResponse)
        d.addErrback(self.noResponse)

    def getResponse(self, response):
        global protocol
        global delay
        getClient = GetAgent(protocol, response.payload)

    def noResponse(self, failure):
        print('Failed to fetch resource for SubmitAgent:')
        print(failure)
        reactor.stop()


class SearchAgent:
    ###################################################################
    # The SearchAgent attempts to obtain the status of the server.
    #
    # If the server does not respond an error message is displayed 
    # and execution stops.
    #
    # If the server responds with no available prediction data ("NaN")
    # or with an "Empty" status, the SubmitAgent is called to offload
    # execution to the server.
    #
    # If the server responds with a prediction regarding the mean 
    # waiting time, the SubmitAgent is called only when offloading
    # the execution is deemed more efficient than executing locally.
    ###################################################################  
    
    def __init__(self, protocol):
        self.protocol = protocol
        reactor.callLater(0, self.requestResource)

    def requestResource(self):
        request = coap.Message(code=coap.GET, payload="Status")
        request.opt.uri_path = (b'serve',)
        request.opt.observe = 0
        request.remote = (ip_address("192.168.1.185"), coap.COAP_PORT)
        d = protocol.request(request)
        d.addCallback(self.checkResponse)
        d.addErrback(self.noResponse)

    def checkResponse(self, response):
        global protocol
        global delay
        server_response = response.payload.split(":", 1)[1]
        delay = ACCELERATED_TIME

        if server_response == "NaN":
            print("No info from server, sending packets.")
            searchClient = SubmitAgent(protocol)
        elif server_response == "Empty":
            print("No clients in the system, sending packets.")
            searchClient = SubmitAgent(protocol)
        else:
            server_exec_time = float(server_response)
            if server_exec_time < EXECUTION_TIME:
                delay = server_exec_time
                print("Sending data to server.Estimated exec. time: "+ str(server_exec_time))
                searchClient = SubmitAgent(protocol)
            else:
                print("Server busy, running locally.")
                os.system("gcc load.c -o load")
                os.system("./load "+str(EXECUTION_TIME))
                reactor.stop()

    def noResponse(self, failure):
        print('Failed to fetch resource for SearchAgent:')
        print(failure)
        reactor.stop()

if __name__ == '__main__':
    ############################################################################
    # These values are arbitrary and can be changed for simulation purposes.
    # The execution times of the load.c file follow an exponential distribution,
    # since they are modelled as a Poisson process.
    ############################################################################
    mean = 2.0
    ACCELERATION_FACTOR = 0.35
    EXECUTION_TIME = random.expovariate(1.0/mean)
    ACCELERATED_TIME = EXECUTION_TIME - ACCELERATION_FACTOR * EXECUTION_TIME

    print("ACCELERATION_FACTOR = ", ACCELERATION_FACTOR)
    print("EXECUTION_TIME = ", EXECUTION_TIME)
    print("ACCELERATED_TIME = ", ACCELERATED_TIME)

    endpoint = resource.Endpoint(None)
    protocol = coap.Coap(endpoint)

    client = SearchAgent(protocol)
    reactor.listenUDP(61616, protocol)
    reactor.run()