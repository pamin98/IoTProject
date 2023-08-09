'''
Created on 13-01-2020

@author: Panagiotis Minaidis
'''

import os
import random
import subprocess
import sys
import time

############################################################################
# The time delay between two consecutive program executions follows an 
# exponential distribution, since it is modelled as a Poisson process.
############################################################################
if __name__ == '__main__':
	mean = 2.0
	cnt = 0
	lost_packets = 0
	try:
		while True:
			cnt = cnt + 1
			delay = random.expovariate(1.0/mean)
			print("No "+str(cnt)+ " (" + str(delay) + ")")
			time.sleep(delay)
			try:
				subprocess.call(["python","client.py"])
			except:
				lost_packets = lost_packets + 1
				print("Lost packets: "+ str(lost_packets))
	except KeyboardInterrupt:
		file = open("lost_packets.txt", "a+")
		file.write("Packets lost: " + str(lost_packets))
		file.close()
		print("Interrupted.\n")
