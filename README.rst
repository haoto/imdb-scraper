==========================
IMDb Message Board Scraper
==========================

IMDb message board scraper written for scrapy. Use this to back up the entire site before its message board shuts down on 2017/2/20.

Before you start, there are other efforts too
---------------------------------------------
The Archive Team is one of the groups actively backing up the message boards right now. You can see their progress and help out `here`__.
.. __: http://tracker.archiveteam.org/imdb/

Usage
-----
Option 1
~~~~~~~~
Deploy on a scrapyd server or on Scrapy Cloud. Be aware that you'd be giving Amazon money indirectly if the servers are hosted on AWS. As crawling the entire site takes a very long time, it's required to split the job into many smaller ones and run them concurrently.

Option 2
~~~~~~~~
Install scrapy. Navigate to the top level of the project directory containing scrapy.cfg and run:::
	scrapy crawl boards -a num_votes="MIN_VOTES,MAX_VOTES" -a release_date="YYYY-MM-DD,YYYY-MM-DD" -o output.jl -t jsonlines -L INFO

Spider arguments
~~~~~~~~~~~~~~~~
The spider comes with two arguments num_votes and release_date to filter which movie boards to back up.

release_date
	The range of date a movie is first released. Format is "YYYY-MM-DD,YYYY-MM-DD". "YYYY" is a shorthand of "YYYY-01-01,YYYY-12-31". You can leave either of the bounds empty. Defaults to no filter.

num_votes
	The number of votes received for a movie. Specifying "100,200" means from 100 to 200 votes. You can leave either of the bounds emtpy. Specifying "100" means exactly 100 votes. Defaults to "100," meaning at least 100 votes.

You can test your search criteria `here`__. Note that the title search page the spider relies on does not show results beyond the 10,000th one. So you need to set search arguments in a way that no more than 10,000 titles are found.
.. __: http://www.imdb.com/search/title

Output item format
------------------
Each item contains one page of a potentially multe-page discussion thread with the following members:
- boardId is the IMDb title ID the thread belongs to.
- id is the thread ID.
- title is the thread title.
- page is the page of the thread.
- body is the thread cotent compressed with zlib, then encoded in base64. To decompress, in python:::
	body = item['body']
	bodyHtml = zlib.decompress(body.decode('uu'))

Note that the thread content comes in the original HTML format. Further parsing needs to be done to extract individual posts.

Note also that depending on how the scrapy server schedules requests, the threads may not be sorted in any particular order. To order them properly, parse the date of posts in the thread content.

