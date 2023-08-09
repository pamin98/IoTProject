'''
Created on 20-12-2019

@author: Panagiotis Minaidis
'''

from datetime import datetime
import multiprocessing
import os
import sys
import time

from twisted.internet import defer
from twisted.internet import reactor
from twisted.python   import log

import txthings.coap as coap
import txthings.resource as resource

################################################################################
# The server consists of 4 running processes:
#     - Frontend service
#     - Backend service
#     - Benchmark service
#     - Queue Model
#
# The Frontend service receives all the requests of the client nodes.
# On GET Status requests, it returns an estimation of the mean waiting time,
# if available. On GET ID requests, it either returns the requested program's
# results or a "Not available" message. On PUT requests, it saves the received
# source code and notifies the backend via a shared queue.
#
# The Backend waits for new requests to be received by the shared queue. Each
# request is processed by compiling the given source code and running it. 
# Timestamps of the runs start and finish times are saved in a file for the
# Benchmark service.
#
# The Benchmark service monitors the timestamp file and creates a dictionary
# of known hosts and the delays of their submitted programs.
#
# The Queue Model runs every 7 minutes and digests all the data stored in 
# the host dictionary of the Benchmark. It computes mean execution times of
# all the known hosts, as well as calculates the mean Sojourn time. When the
# waiting queue of the frontend only contains known hosts, then the predicted
# waiting time is the sum of their mean execution times. When the waiting queue
# contains at least one unknown host, then the mean sojourn time is the best
# prediction the system can provide to the client.
################################################################################

class ServiceResource (resource.CoAPResource):
	def __init__(self, results_dictionary, waiting_queue, arrivals, avg_exec_dict):
		resource.CoAPResource.__init__(self)
		self.visible = True
		self.buffer = ""
		self.status = "Ready"
		self.testcnt = 0

	def render_GET(self, request):
		client_host, client_port = request.remote
		self.buffer = request.payload
		req = self.buffer.split(":", 1)
		if req[0] == "Status":
			try:
				delay = avg_exec_dict[str(client_host)]
				client_ip = []
				if avg_exec_dict["SOJOURN"] == "NaN":
					response = coap.Message(code=coap.CONTENT, payload="Average waiting time:NaN")
				else:
					for entry in waiting_queue:
						client_ip.append((entry.split("\n", 1))[0])
					if not client_ip:
						response = coap.Message(code=coap.CONTENT, payload="Average waiting time:Empty")
					else:
						for client in client_ip:
							try:
								delay += avg_exec_dict[client]
							except KeyError:
								delay = avg_exec_dict["SOJOURN"]
								break
						response = coap.Message(code=coap.CONTENT, payload="Average waiting time:"+str(delay))
			except KeyError:
				if avg_exec_dict["SOJOURN"] == "NaN":
					response = coap.Message(code=coap.CONTENT, payload="Average waiting time:NaN")
				else:
					response = coap.Message(code=coap.CONTENT, payload="Average waiting time:"+str(avg_exec_dict["SOJOURN"]))
		elif req[0] == "ID":
			try:
				ans = results_dictionary[str(client_host)+":"+req[1]]
				response = coap.Message(code=coap.CONTENT, payload=ans)
				if ans != "Not available.":
					os.system("rm test"+req[1]+" client_test"+req[1]+".c output"+req[1]+".txt")
					del results_dictionary[str(client_host)+":"+req[1]]
			except KeyError:
				response = coap.Message(code=coap.BAD_REQUEST, payload="Bad request.")
		else:
			response = coap.Message(code=coap.NOT_IMPLEMENTED, payload="Request type not available.")
		return defer.succeed(response)

	def render_PUT(self, request):
		timestamp = (datetime.now()).strftime("%d/%m/%Y, %H:%M:%S.%f")
		arrivals.append(datetime.now())
		client_host, client_port = request.remote
		request_id = self.submit_request(request, client_host, timestamp)
		results_dictionary[str(client_host)+":"+str(request_id)] = "Not available."
		
		response = coap.Message(code=coap.CHANGED, payload="ID:"+str(request_id))
		return defer.succeed(response)

	def submit_request(self, request, client_host, arrival):
		self.buffer = request.payload
		client_host, client_port = request.remote
		split_program = self.buffer.split("\n",1)
		client_input = split_program[0][8:]
		client_program = split_program[1]
		count = self.testcnt
		self.testcnt += 1
		
		program_file = open("client_test"+str(count)+".c", "a+")
		program_file.write(client_program)

		waiting_queue.append(str(client_host)+"\n"+str(count)+"\n"+client_input+"\n"+arrival)	
		program_file.close()
		return count

class CoreResource(resource.CoAPResource):

    def __init__(self, root):
        resource.CoAPResource.__init__(self)
        self.root = root

    def render_GET(self, request):
        data = []
        self.root.generateResourceList(data, "")
        payload = ",".join(data)
        log.msg("%s", payload)
        response = coap.Message(code=coap.CONTENT, payload=payload)
        response.opt.content_format = coap.media_types_rev['application/link-format']
        return defer.succeed(response)

# Resource tree creation
def server_frontend(results_dictionary, waiting_queue, arrivals, avg_exec_dict):
	log.startLogging(sys.stdout)
	root = resource.CoAPResource()

	serve = ServiceResource(results_dictionary, waiting_queue, arrivals, avg_exec_dict)
	root.putChild('serve', serve)

	endpoint = resource.Endpoint(root)
	reactor.listenUDP(coap.COAP_PORT, coap.Coap(endpoint)) #, interface="::")
	reactor.run()

def server_backend(results_dictionary, waiting_queue):
	while True:
		while len(waiting_queue) == 0:
			pass
		print("[BACKEND] New request received.")
		data_file = open("requests.txt", "a+")
		timestamp = (datetime.now()).strftime("%d/%m/%Y, %H:%M:%S.%f")
		tmp = waiting_queue[0]
		param_lst = tmp.split("\n",3)
		client = param_lst[0]
		request_id = param_lst[1]
		client_input = param_lst[2]
		arrival = param_lst[3]

		data_file.write(client + "\n" + arrival + "\n" + timestamp)
		print("[BACKEND] Compiling and executing.")
		os.system("gcc client_test"+request_id+".c -o test"+request_id+" >> output"+request_id+".txt")
		os.system("./test"+request_id+" "+client_input+" >> output"+request_id+".txt")

		out_file = open("output"+request_id+".txt", "a+")
		results_dictionary[client+":"+request_id] = out_file.read()
		out_file.close()
		timestamp = (datetime.now()).strftime("%d/%m/%Y, %H:%M:%S.%f")
		data_file.write("\n"+timestamp+"\n")
		data_file.close()
		tmp = waiting_queue.pop(0)
    	
def server_benchmark(timestamp_dict):
	print("[BENCHMARK] Init.")
	file = open("requests.txt", "a+")
	while True:
		time_file = open("timestamps.txt", "a+")
		host = ((file.readline()).split("\n",1))[0]
		if not host:
			time.sleep(1)
			time_file.close()
			continue
		arrival = file.readline()
		start = file.readline()
		finish = file.readline()
		while not start:
			start = file.readline()
		while not finish:
			finish = file.readline()
		print("[BENCHMARK] New timestamps received.")
		arrivald = datetime.strptime(arrival, "%d/%m/%Y, %H:%M:%S.%f\n")
		startd = datetime.strptime(start, "%d/%m/%Y, %H:%M:%S.%f\n")
		finishd = datetime.strptime(finish, "%d/%m/%Y, %H:%M:%S.%f\n")
		time_file.write(host)
		tmp = startd - arrivald
		time_file.write(str(tmp.total_seconds())+"\n")
		tmp = finishd - startd 
		time_file.write(str(tmp.total_seconds())+"\n")
		time_file.close()
		try:
			measures = timestamp_dict[host]
			measures.append(tmp.total_seconds())
			timestamp_dict[host] = measures
		except KeyError:
			lst = []
			lst.append(tmp.total_seconds())
			timestamp_dict[host] = lst

def server_queue_model(timestamp_dict, arrivals, avg_exec_dict):
	avg_exec_dict["SOJOURN"] = "NaN"
	print("[QUEUE MODEL] Created entry for sojourn")
	total_msr = 0
	total_len_exec = 0
	arrivals_interval = 420
	while True:
		time.sleep(arrivals_interval)
		print("[QUEUE MODEL] Init computing.")
		lamda = len(arrivals) / arrivals_interval
		arrivals = []
		key_lst = timestamp_dict.keys()
		for key in key_lst:
			msr = timestamp_dict[key]
			timestamp_dict[key] = []
			total_len_exec += len(msr)
			total_msr += sum(msr)
			if len(msr) > 0:
				avg_exec = sum(msr) / len(msr)
				avg_exec_dict[key] = avg_exec
		mean = total_msr / total_len_exec
		avg_exec_dict["SOJOURN"] = 1 / (mean - lamda)
		print("[QUEUE MODEL] Predictions updated.")
	

if __name__ == '__main__':

	manager = multiprocessing.Manager()

	results_dictionary = manager.dict()
	time_dict          = manager.dict()
	arrivals           = manager.list()
	avg_exec_dict      = manager.dict()
	waiting_queue      = manager.list()

	p = multiprocessing.Process(target=server_frontend,    args=(results_dictionary, waiting_queue, arrivals, avg_exec_dict))
	q = multiprocessing.Process(target=server_backend,     args=(results_dictionary, waiting_queue))
	r = multiprocessing.Process(target=server_benchmark,   args=(time_dict,))
	z = multiprocessing.Process(target=server_queue_model, args=(time_dict, arrivals, avg_exec_dict))

	p.start()
	q.start()
	r.start()
	z.start()

	p.join()
	q.join()
	r.join()
	z.join()

