import argparse
import asyncio
import signal

import isodate

from . import Test


def parse_duration(field, duration):
	try:
		if duration.startswith('P'):
			dv = duration 
		else:
			if duration.startswith('.'):
				dv = 'PT0' + duration
			else:
				dv = 'PT' + duration
		
		return isodate.parse_duration(dv)
	except isodate.isoerror.ISO8601Error:
		parser.error("invalid %s value '%s'" % (field, duration))
	

parser = argparse.ArgumentParser(prog='httpload', description='Put load your webservers')
parser.add_argument('-t', '--target', required=True)
parser.add_argument('-d', '--delay', default='0S')
parser.add_argument('-r', '--rampup', type=float, default=1)
parser.add_argument('-c', '--connections', type=int, default=1)
parser.add_argument('-l', '--length', default='60S')
parser.add_argument('-rc', '--reconnect', type=bool, default='no')

args = parser.parse_args()

args.delay = parse_duration('delay', args.delay)
args.length = parse_duration('length', args.length)
	
test = Test(args)
loop = asyncio.get_event_loop()
loop.add_signal_handler(signal.SIGINT, test.stop)
test.start()