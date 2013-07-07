import re
import sys
import argparse
from urllib.request import urlopen
from bs4 import BeautifulSoup
from collections import defaultdict

hp_url = 'http://www.fanfiction.net/s/5782108/1/Harry-Potter-and-the-Methods-of-Rationality'
m_hp_url = hp_url.replace('www.fanfiction.net', 'm.fanfiction.net')

full_data = urlopen(hp_url).readall()

# for m.fanfiction.net:
# <div id=content><center><b>Harry Potter and the Methods of Rationality</b> by <a href='/u/2269863/'>Less Wrong</a></center>

# for www.fanfiction.net
# <SELECT id=chap_select title="Chapter Navigation" Name=chapter onChange="self.location = '/s/5782108/'+ this.options[this.selectedIndex].value + '/Harry-Potter-and-the-Methods-of-Rationality';"><option  value=1 selected>1. A Day of Very Low Probability<option  value=2 >2. Everything I Believe Is False<option  value=3 >3. Comparing Reality To Its Alternatives

def build_arg_parser():
   parser = argparse.ArgumentParser(description="Convert a FanFiction.net story to a .mobi file for Kindle.")
   parser.add_argument('url', metavar='URL', type=str, help="A FanFiction.net story URL")
   return parser

def get_ff_story_chapter_names(html_content):
	chapter_numbers = [int(option["value"]) for option in html_content.find(id='chap_select').find_all('option')]
	chapter_names = [option.contents[0] for option in html_content.find(id='chap_select').find_all('option')]
	return sorted(zip(chapter_numbers, chapter_names))

url_regex = "https?://www.fanfiction.net/[^\/]/\\d+/"
def get_chapter_url(url, chapter_num):
	return re.search(url_regex, hp_url).group() + str(chapter_num)

def get_ff_story_chapter_html(html_content):
	return html_content.find(id="storytext")

def make_chapter_html(chapter_title, chapter_html):
	html = BeautifulSoup("<html><body><h1 id='chapter_title'/></body></html>")
	html.find(id='chapter_title').string = chapter_title
	html.body.append(chapter_html)
	return html

def chapter_link(num):
	return "chapter-{}.html".format(num)

def make_toc_html(title, author, chapters):
	html = BeautifulSoup("<html><body><h1 id='title'/><h2 id='author'/><ol id='chapter_list'/></body></html>")
	html.find(id='title').string = title
	html.find(id='author').string = author

	chapter_list = html.find(id='chapter_list')
	for chapter_num, chapter_title in chapters:
		list_item = chapter_list.new_tag("li")
		link = list_item.new_tag("a", href=chapter_link(chapter_num))
		link.string = chapter_title
		list_item.append(link)
		chapter_list.append(list_item)
	return html

def make_book_opf(title, author, chapters, description, publisher):
	return ""

def make_toc_ncx(title, author, chapters):
	return ""

def make_ncx_navmap(chapters):
	return make_ncx_toc() + '\n'.join([make_ncx_chapter(number, title) for number,title in chapters])

def make_ncx_toc():
	return make_ncx_navpoint(1, "Table of Contents", 'toc.html')

def make_ncx_chapter(number, title):
	return make_ncx_navpoint(number, title, 'chapter-%d.html' % number)

def make_ncx_navpoint(number, title, html_name):
	return '\n'.join((
		'	<navPoint id="navpoint-%d" playOrder="%d">' % (number,number),
		'		<navLabel>',
		'			<text>%s</text>' % title,
		'		</navLabel>',
		'		<content src="%s"/>' % html_name,
		'	</navPoint>'))

if __name__ == "__main__":
	parser = build_arg_parser()
	args = parser.parse_args()
	url = args.url
	if "fanfiction.net" not in url.lower():
		print("Error:",url,"is not a fanfiction.net url")
		parser.exit()

	html = BeautifulSoup(full_data)
	chapters = get_ff_story_chapter_names(html)
	for chapter_num, chapter_title in chapters:
		html = BeautifulSoup(urlopen(get_chapter_url(url, chapter_num)))
		chapter_html = get_ff_story_chapter_html(html)
		with open('out/' + chapter_link(chapter_num),'w') as outputfile:
			print(make_chapter_html(chapter_title, chapter_html), file=outputfile)
		break


# ffparser.feed(data)

# book_outline = make_outline(ff_url)
# chapter_urls = book_outline.get_chapter_urls()
# kindle_book = KindleBook(book_outline)

# for chapter_url in chapter_urls:
	# current_chapter = next_chapter(current_chapter.url())
	# kindle_chapter = html_to_kindle(current_chapter.html())
	# kindle_book.add_chapter(kindle_chapter)

# kindle_book.finalize()
# kindle_book.write(file_name)