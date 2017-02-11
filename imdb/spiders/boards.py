from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.spidermiddlewares.httperror import HttpError
from imdb.items import ThreadItem
import time
import re
import zlib

class ImdbSpider(Spider):
	name = "boards"

	allowed_domains = ["www.imdb.com"]

	def __init__(self, release_date='', num_votes='100,', *args, **kwargs):
		super(ImdbSpider, self).__init__(*args, **kwargs)
		self.retries = 0
		self.maxRetries = 100
		self.reNums = re.compile('\\d+')
		# sort by release_date ascending; exclude individual TV episodes
		self.start_urls = ["http://www.imdb.com/search/title?count=200&release_date=" + release_date + "&num_votes=" + num_votes + "&sort=release_date,asc&title_type=feature,tv_movie,tv_series,tv_special,mini_series,documentary,game,short,video"]

	def start_requests(self):
		for u in self.start_urls:
			yield Request(u, callback = self.parse, errback = self.errback)

	def errback(self, failure):
		if failure.check(HttpError):
			response = failure.value.response
			if response.status >= 500: # server error
				self.retries += 1
				if self.retries > self.maxRetries:
					print "Failed too many times. Giving up."
					self.retries = 0
				else:
					url = response.url
					throttleDelay = 0.5 * self.retries
					print "Server error. Sleeping for " + str(throttleDelay) + " before next retry. url: " + url
					time.sleep(throttleDelay)
					yield Request(url, callback = self.parse, errback = self.errback, dont_filter=True)
			else:
				print 'ERROR: HTTP' + str(response.status)

	def isImdbDead(self, response):
		title = response.selector.xpath('//title/text()').extract()
		if title == "IMDb - D'oh":
			print "IMDb dead"
			return True
		elif title == "Error":
			print "IMDb dead"
			return True
		elif not response.selector.xpath('//a').extract():
			print "IMDb dead"
			return True
		return False

	def parseThread(self, response):
		pidx = response.url.rfind('?p=')
		if pidx == -1: # first page
			curpage = 1
		else:
			curpage = int(response.url[pidx+3:])

		# save thread body
		item = ThreadItem()
		i = response.url.find('/tt')
		item["boardId"] = response.url[i+1:i+10] # ttXXXXXXX
		i = response.url.rfind('/')
		ids = self.reNums.search(response.url[i+1:])
		if ids:
			item["id"] = ids.group(0)
		item["page"] = curpage
		item["title"] = response.selector.xpath('//div[contains(@class, "title ")]/a/text()').extract()[0]
		item["body"] = zlib.compress(response.selector.xpath('//div[contains(@class, "thread mode-thread")]').extract()[0].encode('utf8')).encode('uu')
		yield item

		# find next page
		pages = response.selector.xpath('//a[contains(@href, "?p=")]/@href').extract()
		for p in pages:
			if p.rfind('last') != -1:
				continue
			pid = self.reNums.search(p[p.rfind('?p=')+3:])
			if pid:
				page = int(pid.group(0))
				if page > curpage:
					# found next page
					url = 'http://www.imdb.com' + p
					yield Request(url, callback = self.parse, errback = self.errback)
					break

	def parseBoard(self, response):
		pidx = response.url.rfind('?p=')
		if pidx == -1: # first page
			curpage = 1
		else:
			curpage = int(response.url[pidx+3:])
		title = response.selector.xpath('//h1/a/text()').extract()
		if len(title) > 0:
			print "Board: " + title[0].encode('utf8') + ": page " + str(curpage)

		threads = response.selector.xpath('//a[contains(@href, "/board/thread/")]/@href').extract()
		threadsParsed = []
		for t in threads:
			# filter out links to thread pages
			if t.rfind('?') != -1:
				continue
			if not t in threadsParsed:
				threadsParsed.append(t)
				url = 'http://www.imdb.com' + t
				yield Request(url, callback = self.parse, errback = self.errback)
		# find next page
		pages = response.selector.xpath('//a[contains(@href, "/?p=")]/@href').extract()
		for p in pages:
			pid = self.reNums.search(p[p.rfind('?p=')+3:])
			if pid:
				page = int(pid.group(0))
				if page > curpage:
					# found next page
					url = 'http://www.imdb.com' + p
					yield Request(url, callback = self.parse, errback = self.errback)
					break

	def parse(self, response):
		if self.isImdbDead(response):
			yield Request(response.url, callback = self.parse, errback = self.errback,
					dont_filter=True)
			return
		if response.url.find('/board/thread/') != -1:
			for r in self.parseThread(response):
				yield r
		elif response.url.find('/board/') != -1:
			for r in self.parseBoard(response):
				yield r
		elif response.url.find('/search/title?') != -1:
			titlesToCrawl = []
			titles = response.selector.xpath('//a[contains(@href, "/title/")]/@href').extract()
			for tt in titles:
				# title id: ttXXXXXXX
				if not tt[7:16] in titlesToCrawl:
					titlesToCrawl.append(tt[7:16])

			for tt in titlesToCrawl:
				url = 'http://www.imdb.com/title/' + tt + '/board/'
				yield Request(url, callback = self.parse, errback = self.errback)

			# next page of titles
			nextPage = response.selector.xpath('//a[contains(@class, "lister-page-next")]/@href').extract()
			if len(nextPage) == 2: # two of the same link
				url = 'http://www.imdb.com/search/title' + nextPage[0]
				yield Request(url, callback = self.parse, errback = self.errback)
		else:
			print 'DERP?'

