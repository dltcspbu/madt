import requests
import time

target = 3 * (30/10)

for delay in range(100, 5000, 300):
	print("Testing with delay =", delay)
	requests.post('http://localhost/lab/restart', 
		json={"name": "kademlia_new", "tc_options": {"delay": delay}})
	
	time.sleep(30)
	stats = requests.get('http://localhost/lab/stats', 
		params={"name": "kademlia_new"}).json()
	successfull_messages = stats['status_count']['0']
	if successfull_messages < target:
		print('Only {0} messages was sent, need {1}'
			.format(successfull_messages, target))
		break
	else: 
		print('{0} messages was sent, need {1}, moving on'
			.format(successfull_messages, target))
