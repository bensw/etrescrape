from bs4 import BeautifulSoup as bs4
import urllib2
import re
import sqlite3
import datetime
import boto.ses
from email_list_secret import *

"""CREATE TABLE beers (id INTEGER PRIMARY KEY, name text, qty real, price real,last_updated text);"""

URLS = ["http://www.bieresgourmet.be/catalog/index.php?main_page=index&manufacturers_id=14", # Cantillon
        "http://www.bieresgourmet.be/catalog/index.php?main_page=index&manufacturers_id=3", #3F
	"http://www.bieresgourmet.be/catalog/index.php?main_page=index&manufacturers_id=66", #Tilquin
	"http://www.bieresgourmet.be/catalog/index.php?main_page=index&manufacturers_id=10"] #Struise
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


def render(changes, new_beers):
	connection = boto.ses.connect_to_region('us-east-1')
	if connection == None:
		print "Couldn't connect to SES"
		return
	subject = "Etre Gourmet Update!"
	bodyText = ''

	for item in changes:
		for attr in changes[item]:
			if changes[item][attr][0] != changes[item][attr][1]:
				if attr == "qty":
					if changes[item][attr][1] == 0:
						bodyText += "%s is now SOLD OUT!\n" % (item)
					elif changes[item][attr][0] < changes[item][attr][1]:
						bodyText += "Quantity INCREASED for %s, now %s in stock!\n" % (item, changes[item][attr][1])
				else:
					bodyText += "%s CHANGED FOR %s!!! WAS %s NOW IS %s \n" %(attr.title(), item, changes[item][attr][0], changes[item][attr][1])
	for beer in new_beers:
		bodyText += "New beer found! There are %d %s at %f euros!\n" % (beer['qty'], beer['name'], beer['price'])
	if bodyText != "":
		connection.send_email(MYEMAIL, subject, bodyText, EMAILS)
	else:
		print "No Message Sent"


def main():

	now = str(datetime.datetime.now())
	conn = sqlite3.connect(DIR + "scrape.db")
	conn.row_factory=sqlite3.Row
	
	c = conn.cursor()
	changes = {}
	new_beers = []
	items = []

	# Add beers to items from each url
	for url in URLS:
		soup = bs4(urllib2.urlopen(url).read())
		print "Found %s Items..." % (total_items(soup))
		items += get_items(soup)

		# See if there are multiple pages		
		page = 2
		while (int(total_items(soup)) > len(items)):
			items += get_items(bs4(urllib2.urlopen(url + "&sort=20a&page=%d" % page ).read()))
			page += 1

	# Loop over beers found
	for item in items:
		# See if the beer exists in the database
		entry = c.execute("SELECT * FROM beers WHERE name = ?", [item['name']]).fetchall()
		if (len(entry) == 0): # If it doesn't insert it into the data base 
			c.execute("INSERT INTO beers (last_updated, name, qty, price) VALUES (?, ?, ?, ?)", [now, item['name'], item['qty'], item['price']])
			new_beers.append({"name":item['name'], "qty":item['qty'], "price":item['price']})
			# print "New beer found! name: %s qty: %d price: %f" % (item['name'], item['qty'], item['price'])
		elif (len(entry) == 1): # If it does exist
			e = entry[0]
			# Loop over the keys that are important (not id, time)
			for key in e.keys()[1:-1]: 
				if e[key] != item[key]:
					if item['name'] in changes.keys():
						changes[item['name']][key] = [str(e[key]), str(item[key])]
					else:
						changes[item['name']] = {key:[str(e[key]), str(item[key])]}
			c.execute("UPDATE beers SET name=?, qty=?, price=?, last_updated=? WHERE id = ?", [item['name'], item['qty'], item['price'], now, entry[0][0]])
		

	# Rendering
	render(changes, new_beers)

	# Commit and close the db cursor
	conn.commit()
	conn.close()

if __name__ == "__main__":
	main()
