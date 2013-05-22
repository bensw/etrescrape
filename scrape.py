from bs4 import BeautifulSoup as bs4
import urllib2
import re
import sqlite3
import datetime

"""CREATE TABLE beers (id INTEGER PRIMARY KEY, name text, qty real, price real,last_updated text);"""

URLS = ["http://www.bieresgourmet.be/catalog/index.php?main_page=index&manufacturers_id=14", # Cantillon
		"http://www.bieresgourmet.be/catalog/index.php?main_page=index&manufacturers_id=3"]  # 3F

def total_items(soup):
	return soup.select("#productsListingTopNumber")[0].select("strong:nth-of-type(3)")[0].text

def get_items(soup):
	r =[]
	for tr in (soup.select(".productListing-odd") + soup.select(".productListing-even")):
		item = {}
		tds = tr.select("td")
		item['qty'] = int(tds[0].text) # do I want to ignore items with 0 quantity
		item['weight'] = float(tds[2].text) # do I care about the weight?
		item['name'] = tds[3].select("a")[0].text
		item['price'] = float(re.search("\d+\.\d+", tds[4].text).group(0))
		r.append(item)
	return r

def main():
	now = str(datetime.datetime.now())
	conn = sqlite3.connect("scrape.db")
	c = conn.cursor()
	for url in URLS:
		soup = bs4(urllib2.urlopen(url).read())
		print "Found %s Items..." % (total_items(soup))
		items = get_items(soup)

		## See if there are multiple pages		
		page = 2
		while (int(total_items(soup)) > len(items)):
			print total_items(soup), len(items), page
			items += get_items(bs4(urllib2.urlopen(url + "&sort=20a&page=%d" % page ).read()))
			page += 1

		# Loop over beers found
		for item in items:
			entry = c.execute("select * from beers where name = ?", [item['name']]).fetchall()
			if (len(entry) == 0):
				c.execute("INSERT INTO beers (last_updated, name, qty, price) VALUES (?, ?, ?, ?)", [now, item['name'], item['qty'], item['price']])
				print ("Inserted name=%s qty=%d price=%f" %(item['name'], item['qty'], item['price']))
			elif (len(entry) == 1):
				changed=0
				e = {"name":entry[0][1], "qty":entry[0][2], "price":entry[0][3]}
				for key in e:
					if e[key] != item[key]:
						print "%s CHANGED FOR %s!!! WAS %s NOW IS %s" %(key, item['name'], str(e[key]), str(item[key]))
						changed=1
				c.execute("UPDATE beers SET name=?, qty=?, price=?, last_updated=? WHERE id = ?", [item['name'], item['qty'], item['price'], now, entry[0][0]])
				if changed == 0:
					print "NOTHING CHANGED for beer %s" %(item['name'])


#			print "%s:%d Remaining: Cost:%f" %(item['name'], item['quantity'], item['price'])
	conn.commit()
	conn.close()

if __name__ == "__main__":
	main()
