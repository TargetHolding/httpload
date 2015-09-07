'''
	httpload is a small straight forward python tool to generate some HTTP load
	with connections kept alive and _not_ shared between clients.
	
	To use httpload start it as a python module, e.g.:
		
		python -m httpload ...
		
	Use the -h flag to print the usage information.
'''

import asyncio
from datetime import timedelta, datetime
import re

import aiohttp

from .metrics import Metric, CategoriesMetric


class Test():
	'''
		The main class for performing a http load test. Use .start(...) to
		commence the test and .stop() to stop it.
	'''
	
	def __init__(self, opts):
		self.opts = opts
		self._workers = []
		self._stop = False
		self.stats = Stats(opts, timedelta(seconds=10))

	
	def start(self, loop=None):
		'''
			Start the test on the given or default event loop.
		'''
		self._stop = False
		loop = loop or asyncio.get_event_loop()
		loop.run_until_complete(self.run())
	
	
	def stop(self):
		'''
			Signal te test to stop
		'''
		print('')  # to move beyond ^C in the console
		self._stop = True
	
	
	@asyncio.coroutine
	def run(self):
		'''
			Drive the http load test by initiating the configured amount of
			connections and workers. When the test is completed or is stopped
			the connections and workers are closed / cancelled. 
		'''
		self.start = datetime.now()
		
		# the base connection pool to draw connections from
		connector = aiohttp.connector.TCPConnector(
			# make the keep alive timeout long enough
			keepalive_timeout=self.opts.length * 2,
			# make sure enough connections are pooled
			limit=self.opts.connections,
		)
		
		print(
			'starting httpload, creating', self.opts.connections,
			 'connections', 'at', self.opts.rampup, 'connections / second'
		)
		
		# start the workers
		self._workers = yield from self.create_workers(connector)
		
		# wait until no more time remaining in test or was stopped
		while self.stats.time_remaining and not self._stop:
			yield from asyncio.sleep(.1)
		
		# make sure the stop flag is set and recored the current time
		self._stop = True
		self._time_stopped = datetime.now()
		
		# allow workers to top
		yield from asyncio.sleep(.1)
		
		# close the transport and the workers
		connector.close()
		for worker in self._workers:
			worker.stop()

		# print final stats
		print(self.stats.get_basic_stats())
		print(self.stats.get_final_stats())


	@asyncio.coroutine
	def create_workers(self, connector):
		workers = []
		
		# create the connections and start workers for each of them
		for c in range(self.opts.connections):
			# sleep to maintain the ramp up rate
			while not self._stop and c / self.stats.time_running.total_seconds() > self.opts.rampup:
				yield from asyncio.sleep(.1)
			
			# respond to the stop flag
			if self._stop:
				break
			
			# create the session to work on
			session = aiohttp.ClientSession(
				connector=SingleConnector(connector),
				headers={aiohttp.hdrs.CONNECTION: aiohttp.hdrs.KEEP_ALIVE}
			)
			
			# create and start the worker
			worker = Worker(self, session, self.opts.target, self.opts.delay)
			worker.on_close(workers.remove)
			workers.append(worker)
			worker.start()

		# print connection stats
		print('-- created', len(workers), 'connections in', self.stats.time_running, '--')
		
		# return the created workers
		return workers

	@property
	def stopped(self):
		return self._stop



class Stats(object):
	'''
		Statistics for a http load test.
	'''

	def __init__(self, opts, print_interval):
		self._opts = opts
		self._print_interval = print_interval
		
		# time to track
		self.time_started = datetime.now()
		self.time_stopped = None

		# stats to track
		# use received.count for completed and
		# received.total for total bytes received
		self.received = Metric()
		self.failed = Metric()
		self.latency = Metric()
		self.response_codes = CategoriesMetric()
		
		# remember the time of last stat print and the # of requests completed
		self._last_stat = self.time_started
		self._completed_last = 0


	@property
	def time_running(self):
		return datetime.now() - self.time_started
	
	@property
	def time_remaining(self):
		return max(timedelta(), self._opts.length - self.time_running)
	
	
	# @asyncio.coroutine
	def update(self, **kwargs):
		# update each of the statistics
		for k, v in kwargs.items():
			if k == 'response_code':
				self.response_codes.push(v, 1)
			elif v:
				attr = getattr(self, k, None)
				if attr:
					attr.push(v)
		
		# print the intermediary counnts if its time to
		if datetime.now() - self._last_stat > self._print_interval:
			print(self.get_basic_stats())
	
	
	def get_basic_stats(self):
		now = datetime.now()
		
		self._last_stat = self._last_stat or self.time_started
		since_last_stat = (now - self._last_stat).total_seconds()
		completed_since_last_stat = self.received.count - self._completed_last
		
		#msg = '%s reqs completed \tin %s \tat %s/s \t%s failed \t%s kb received (uncompressed) \tat %s kbps' % (
		msg = '%s reqs completed \tin %s \tat %s/s \t%s failed' % (
			self.received.count,
			self.time_running,
			round(completed_since_last_stat / since_last_stat, 1),
			self.failed.count,
		#	round(self.received.total / 1024),
		#	round(self.received.total / 1024 / since_last_stat),
		)
		
		self._last_stat = now
		self._completed_last = self.received.count
		
		return msg
	
	def get_final_stats(self):
		failed = self.failed.count
		failed_rate = round(self.failed.count / self.received.count, 1) if self.received.count else 0
		request_rate = round(self.received.count / self.time_running.total_seconds(), 1)
		
		return '\n'.join((
			'-' * 80,
			'	test duration     = %s' % self.time_running, 
			'	completed         = %s' % self.received.count,
			'	failed            = %s (%s%%)' % (failed, failed_rate),
			'	avg. request rate = %s / second' % request_rate,
			'	latency (mean)    = %s' %  timedelta(seconds=self.latency.mean),
			'	latency (std)     = %s''' % timedelta(seconds=self.latency.std),
			'	response codes / errors:',
			'\n'.join(
				'	   %s = %s' % (cf, self.response_codes.categories[c].count)
				for (cf, c) in sorted(
					(re.sub("([a-z])([A-Z])","\g<1> \g<2>", str(c).replace('Error', '')).lower(), c)
					for c in self.response_codes.categories
				)
			),
			'-' * 80,
		))



class Worker(object):
	'''
		A worker in a http load test.
	'''
	
	def __init__(self, test, session, target, delay):
		self._test = test
		self._session = session
		self._target = target
		self._delay = delay
		self._running = []
		self._on_close = []
	
	
	def start(self):
		if not self._test.stopped:
			task = asyncio.async(self._make_request())
			task.add_done_callback(self._request_done)
			task.add_done_callback(self._running.remove)
			self._running.append(task)
		
	def stop(self):
		self._session.close()
		for task in self._running:
			task.cancel()
	
	def on_close(self, callback):
		self._on_close.append(callback)
	
	def _close(self):
		self._session.close()
		[callback() for callback in self._on_close]
	
	
	@asyncio.coroutine
	def _make_request(self):
		'''
			Make a request to target, update stats, print and sleep to delay.
		'''
		
		# perform the request (async)
		try:
			start = datetime.now()
			response = yield from self._session.get(self._target)
			body = yield from response.read()
			end = datetime.now()
		except (aiohttp.errors.ClientRequestError, aiohttp.errors.ClientResponseError) as e:
			self._test.stats.update(failed=1, response_code=e.__cause__.__class__.__name__)
			raise

		# update stats		
		latency = (end - start).total_seconds()
		self._test.stats.update(
			completed=1,
			latency=latency,
			response_code=response.status,
			failed=not(200 <= response.status <= 400),
			received=len(body)if body else 0
		)
	
		# sleep if neccessary
		sleep = max(0, self._delay.total_seconds() - latency)
		if sleep:
			yield from asyncio.sleep(sleep)
			
	
	def _request_done(self, task):
		'''
			Called on completion of a request. Schedules makeing the next
			requests or cleanup. 
		'''

		# close if cancelled
		if task.cancelled():
			self._close()
			return
		
		# close if exception except for disconnect and opts.reconnect
		exc = task.exception()
		if exc and (isinstance(exc, asyncio.futures.CancelledError) or (
			isinstance(exc.__cause__, aiohttp.errors.ServerDisconnectedError)
			and not self._test.opts.reconnect
		)):
			self._close()
			return

		# start next request if not cancelled or (fatal) exception raised 
		self.start()



class SingleConnector(aiohttp.BaseConnector):
	'''
		A aiohttp connector which holds only a single connection, taken from a
		'parent' connector. Reconnects if the connection is closed. Note that
		releasing the connection does _not_ return it to the parent connector.
	'''
	
	def __init__(self, parent, *args, **kwargs):
		self.parent = parent
		self._loop = parent._loop
		self._share_cookies = parent._share_cookies
		self._connection = None
	
	def close(self):
		if self._connection:
			self._connection.close()
		
	@property
	def closed(self):
		return self._connection.closed if self._connection else False
		
	@asyncio.coroutine
	def connect(self, req):
		if not self._connection or self._connection.closed:
			# get a new connection from the pool 
			self._connection = yield from self.parent.connect(req)
			# make sure the transport isn't returned to the original connector
			self._connection.release = lambda: None
			
		return self._connection
