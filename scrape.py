from bs4 import BeautifulSoup as bs4
import urllib2
import re

URLS = ["http://www.bieresgourmet.be/catalog/index.php?main_page=index&manufacturers_id=14", #Cantillon
		"http://www.bieresgourmet.be/catalog/index.php?main_page=index&manufacturers_id=3"]  #3F

def total_items(soup):
	return soup.select("#productsListingTopNumber")[0].select("strong:nth-of-type(3)")[0].text

def get_items(soup):
	r =[]
	for tr in (soup.select(".productListing-odd") + soup.select(".productListing-even")):
		item = {}
		tds = tr.select("td")
		item['quantity'] = int(tds[0].text) # do I want to ignore items with 0 quantity
		item['weight'] = float(tds[2].text) # do I care about the weight?
		item['name'] = tds[3].select("a")[0].text
		item['cost'] = float(re.search("\d+\.\d+", tds[4].text).group(0))
		r.append(item)
	return r

def main():
	for url in URLS:
		soup = bs4(urllib2.urlopen(url).read())
		print "Found %s Items...." % (total_items(soup))
		items = get_items(soup)
		for item in items:
			print "%s:%d Remaining: Cost:%f" %(item['name'], item['quantity'], item['cost'])


if __name__ == "__main__":
	main()
