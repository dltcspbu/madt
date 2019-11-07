import zmq
import os

class MADT_Client():
	def __init__(self):
		self.madt_ctx = zmq.Context()
		self.madt_sock = self.madt_ctx.socket(zmq.PUSH)
		self.madt_sock.connect('ipc:///lab/lab.sock')

	def send(self, status, log, traffic):
		print('sending', status, log, traffic)
		self.madt_sock.send_json({
	        'hostname': os.environ['HOSTNAME'],
	        'traffic': traffic,
	        'status': status,
	        'log': log })


