from pygeoip import pygeoip

dbfile = 'GeoIP.dat'

def update():
	gzipfile = dbfile + ".gz"
	f = open(gzipfile, 'w')
	dburl = 'http://geolite.maxmind.com/download/geoip/database/GeoLiteCountry/GeoIP.dat.gz'
	import urllib2
	import gzip
	print("Downloading %s ..." %(dburl))
	response = urllib2.urlopen(dburl)
	f.write(response.read())
	f.close()
	print("done!")
	f = gzip.open(gzipfile)
	db = open(dbfile, 'w')
	db.write(f.read())
	f.close()
	db.close()

try:
	f=open(dbfile,'r')
	f.close()
except:
	print("%s doesn't exist, downloading..." % (dbfile))
	update()

def loaddb():
	global geoip
	try:
		geoip = pygeoip.Database('GeoIP.dat')
		return True
	except:
		return False

working = loaddb()


def lookup(ip):
	if not working: return '??'
	addrinfo = geoip.lookup(ip)
	if not addrinfo.country: return '??'
	return addrinfo.country

def reloaddb():
	if not working: return
	loaddb()

#print lookup("37.187.59.77")
#print lookup("77.64.139.108")
#print lookup("8.8.8.8")
#print lookup("0.0.0.0")

