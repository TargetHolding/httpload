HTTP Load
=================

A straight forward python tool to generate some HTTP load with connections kept alive and _not_ shared between clients.

## Requirements:

httpload uses aiohttp which in turn builds on asyncio which is introduced in python 3.4. Furthermore isodate is used to parse ISO 8601 formatted durations given as command line options.

## Installation:



## Usage

Output of `python -m httpload -h`:

```
optional arguments:
  -h, --help            show this help message and exit
  -t TARGET, --target TARGET
  -d DELAY, --delay DELAY
  -r RAMPUP, --rampup RAMPUP
  -c CONNECTIONS, --connections CONNECTIONS
  -l LENGTH, --length LENGTH
  -rc RECONNECT, --reconnect RECONNECT
```

## Example

Example which loads the server(s) at http://www.example.org/ for one hour with 1000 connections. Connections will be started at a rate of approximately 10 every second. The client will reconnect if the server disconnects. On each of these a message is sent every .5 seconds. I.e. the request rate will be approximately 2000 messages / second.

```
python -m httpload \
	--target http://www.example.org/ \
	--length 1H \
	--connections 1000 \
	--rampup 10 \
	--reconnect yes \
	--delay .5S
```

## Example output

httpload writes a line to standard out around every 10 seconds with the total number of complete requests, the time passed, the request rate in the last 10 seconds and the total number of failed requests.

Furthermore a line is written to standard out when the requested number of connections was established.

When httpload completes or when httpload is interrupted (e.g. with CTRL+C or a SIGTERM signal) asummary is written to standard out with:
- the test duration,
- the number of completed and failed request,
- the average request rate over the entire test period,
- the mean latency and the standard deviation
- per HTTP response code and error the total number of occurrences 

```
$ python -m httpload --target https://acceptatie.diatoetsen.nl/home/ --connections 1000 --rampup 10 --length 1H --reconnect yes --delay .5S
starting httpload, creating 1000 connections at 10.0 connections / second
1050 reqs completed 	in 0:00:10.049253 	at 104.5/s 	0 failed
4098 reqs completed 	in 0:00:20.049609 	at 304.8/s 	0 failed
8062 reqs completed 	in 0:00:30.050791 	at 396.4/s 	0 failed
11691 reqs completed 	in 0:00:40.051718 	at 362.9/s 	0 failed
15408 reqs completed 	in 0:00:50.054016 	at 371.6/s 	0 failed
19143 reqs completed 	in 0:01:00.055118 	at 373.5/s 	41 failed
22812 reqs completed 	in 0:01:10.058116 	at 366.8/s 	114 failed
26482 reqs completed 	in 0:01:20.061200 	at 366.9/s 	157 failed
30122 reqs completed 	in 0:01:30.091521 	at 362.9/s 	181 failed
-- created 1000 connections in 0:01:39.952067 --
33429 reqs completed 	in 0:01:40.100291 	at 330.4/s 	253 failed
37435 reqs completed 	in 0:01:50.110527 	at 400.2/s 	366 failed
^C
39036 reqs completed 	in 0:01:54.481615 	at 366.3/s 	388 failed
--------------------------------------------------------------------------------
	test duration     = 0:01:54.481703
	completed         = 39036
	failed            = 388 (0.0%)
	avg. request rate = 341.0 / second
	latency (mean)    = 0:00:00.544008
	latency (std)     = 0:00:04.228234
	response codes / errors:
	   200 = 39036
	   server disconnected = 388
--------------------------------------------------------------------------------
```

