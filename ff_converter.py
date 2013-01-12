import re
import sys
import argparse
from urllib.request import urlopen
from urllib.parse import urlparse, urlunparse
from html.parser import HTMLParser
from collections import defaultdict

class FanFictionNetChapter:
	def __init__(self, number, title, url):
		self._number = number
		self._title = title
		self._url = url
		self._text = None
		self._has_cached_data = False
		self._htmlparser = FanFictionHtmlParser()
	def htmlparser(self):
		return self._htmlparser
	def number(self):
		return self._number
	def title(self):
		return self._title
	def url(self):
		return self._url
	def text(self):
		self._verify_cached()
		return self._htmlparser.chaptertext()
	def _verify_cached(self):
		if self._has_cached_data:	
			return
		self._has_cached_data = True
		html = urlopen(self._url).readall()
		self._htmlparser.feed(html)

class FanFictionNetStory:
	_path_search_regex = "(?P<prefix>/\\w/\\d+)/(?P<chapter>\\d+)/(?P<suffix>.*)"
	def __init__(self, url):
		self._has_cached_data = False
		self._chapters = []

		self._original_url = url.replace('m.fanfiction.net', 'www.fanfiction.net')
		self._mobile_url = url.replace('www.fanfiction.net', 'm.fanfiction.net')

		parsed = urlparse(self._original_url)
		self._url_split = list(parsed)
		self._path_parts = re.search(FanfictionNetStory._path_search_regex, parsed.path).groupdict()
	def _make_chapter_url(self, chapter_index):
		newpath = '/'.join([path_parts['prefix'], str(chapter_index), path_parts['suffix']])
		url_parts = list(self._url_split)
		url_parts[2] = newpath
		return urlunparse(url_parts)
	def chapters(self):
		"""
		Return a list of FanFictionNetChapter objects, in order
		"""
		self._verify_cached()
		return self._chapters
	def story_title(self):
		self._verify_cached()
		return self.htmlparser.story_title()
	def author(self):
		self._verify_cached()
		return self.htmlparser.author()
	def publisher(self):
		return "FanFiction.net"
	def _verify_cached(self):
		if self._has_cached_data:	
			return
		self._has_cached_data = True
		full_data = urlopen(self._original_url).readall()
		mobile_data = urlopen(self._mobile_url).readall()

		titleparser = HierarchyParser(TITLE_STACK)
		titleparser.feed(mobile_data)

		authorparser = HierarchyParser(AUTHOR_STACK)
		authorparser.feed(mobile_data)
		# print("Author:",authorparser.data())

		tocparser = HierarchyParser(TOC_STACK)
		tocparser.feed(full_data)
		
		self.author = authorparser.data()[0]
		self.title = titleparser.data()[0]
		self.chapters = tocparser.data()

def clamp(min, val, max):
	return sorted((min, val, max))[1]

def mapify_attrs(attrs):
	attrs = filter(non_none, attrs)
	return {k:v.replace("\\'","") for k,v in attrs}

def attrs_to_str(attrs):
	attrs = mapify_attrs(attrs)
	if len(attrs) == 0:
		return ""
	return " " + ' '.join("=".join((k,'"' + attrs[k] + '"')) for k in attrs)

def non_none(args):
	return None not in args and None not in set(arg for arg in args)

def matches(tag, attrs, search_frame):
	'''Return True if the tag/attrs match a tag/attrs'''
	attrs = mapify_attrs(attrs)
	if search_frame[0] != tag:
		return False
	test_attrs = search_frame[1]
	if not all(item in attrs.items() for item in test_attrs.items()):
		return False
	return True

class HierarchyParser(HTMLParser):
	def __init__(self, tag_stack):
		HTMLParser.__init__(self)
		self._stack = tag_stack
		self._capture_state = -1
		self._data = []
		self._doprint = False
		self._printcount = 100
		self._nocapture_levels = 0
	def handle_starttag(self, tag, attrs):
		self._incr_tag(tag, attrs)
		if self._nocapture_levels > 0:
			self._print("no capture:",tag, attrs)
		self._enter_capture_state(tag.lower(), attrs)
		self._capture_tag(tag, attrs)
	def handle_endtag(self, tag):
		self._decr_tag()
		self._capture_endtag(tag)
	def _enter_capture_state(self, tag, attrs):
		if self._capture_state < 0 and matches(tag, attrs, self._stack[0]):
			self._print("Capturing at",tag,attrs)
			self._capture_state = self._capture_state + 1
	def _capture_tag(self, tag, attrs):
		if self._in_tag_capture_frame():
			attrs_list = attrs_to_str(attrs)
			html = ''.join(("<", tag, attrs_list, ">"))
			self._data.append(html)
	def _capture_endtag(self, tag):
		if self._in_tag_capture_frame():
			html = ''.join(("</", tag, ">"))
			self._data.append(html)
	def _incr_tag(self, tag, attrs):
		if self._currently_capturing() and matches(tag, attrs, self._closest_frame()):
			self._capture_state = self._capture_state + 1
		elif self._capture_state >= 0:
			self._nocapture_levels = self._nocapture_levels + 1
	def _decr_tag(self):
		if self._currently_capturing():
			self._capture_state = clamp(-1, self._capture_state - 1, self._capture_state)
		elif self._capture_state >= 0:
			self._nocapture_levels = self._nocapture_levels - 1
	def _currently_capturing(self):
		'''Return True if we're in a potential flag capture state. This is if
		1. We've found at least one tag that matches the beginning of our stack and
		2. We haven't started down a node hierarchy that doesn't match our stack.'''
		found_at_least_one = (self._capture_state >= 0)
		in_interesting_nodes = (self._nocapture_levels == 0)
		if found_at_least_one:
			self._print("in_interesting_nodes:", in_interesting_nodes)
		return found_at_least_one and in_interesting_nodes
	def _closest_frame(self):
		idx = clamp(-1, self._capture_state, len(self._stack) - 1)
		if idx < 0:
			self._print("Returning empty frame")
			return ()
		return self._stack[idx]
	def _at_capture_frame(self, flag):
		'''Return True if we're in a frame where we should capture the flag'''
		if self._capture_state < 0:
			return False
		return self._currently_capturing() and flag in self._closest_frame()
	def handle_data(self, data):
		if self._in_text_capture_frame():
			self._print(self._capture_state * '.',data[:50])
			self._data.append(data.strip())
	def data(self):
		return self._data
	def _in_text_capture_frame(self):
		return self._at_capture_frame("CAPTUREDATA")
	def _in_tag_capture_frame(self):
		return self._at_capture_frame("CAPTURETAGS")
	def _print(self, *args):
		if self._doprint and self._printcount > 0:
			self._printcount = self._printcount - 1
			print(*args)

# for m.fanfiction.net
# <div style='padding:5px 10px 5px 10px;' class='storycontent' id='storycontent' ><p>Disclaimer: J. K. Rowling owns Harry Potter

hp_url = 'http://www.fanfiction.net/s/5782108/1/Harry-Potter-and-the-Methods-of-Rationality'
m_hp_url = hp_url.replace('www.fanfiction.net', 'm.fanfiction.net')

def end_tag(matchobj):
	return matchobj.group(0).replace('>','/>')

def end_option_tag(matchobj):
	tagname = matchobj.groupdict()["tag"]
	attrs_and_cdata = matchobj.groupdict()["attrs_and_cdata"]
	whole_thing = ''.join(("<",tagname,attrs_and_cdata,"</",tagname,">"))
	return whole_thing

def sanitize(html):
	html = re.sub('\<(?P<tag>option)(?P<attrs_and_cdata>[^<]+)',end_option_tag, html)
	html = re.sub('\<(hr|br)[^/>]*\>',end_tag, html)
	return html

mobile_data = sanitize(str(urlopen(m_hp_url).readall()).replace('<br>','<br/>'))
full_data = sanitize(str(urlopen(hp_url).readall()))

# for m.fanfiction.net:
# <div id=content><center><b>Harry Potter and the Methods of Rationality</b> by <a href='/u/2269863/'>Less Wrong</a></center>

# for www.fanfiction.net
# <SELECT id=chap_select title="Chapter Navigation" Name=chapter onChange="self.location = '/s/5782108/'+ this.options[this.selectedIndex].value + '/Harry-Potter-and-the-Methods-of-Rationality';"><option  value=1 selected>1. A Day of Very Low Probability<option  value=2 >2. Everything I Believe Is False<option  value=3 >3. Comparing Reality To Its Alternatives

TITLE_STACK = [
	("div",{"id":"content"}),
	("center",{}),
	("b",{}, "CAPTUREDATA"),
	("anything",{})]
AUTHOR_STACK = [
	("div",{"id":"content"}),
	("center",{}),
	("a",{}, "CAPTUREDATA"),
	("anything",{})]
TOC_STACK = [
	("select",{"id":"chap_select"})
	,
	("option",{}, "CAPTUREDATA")
	]
CHAPTERTEXT_STACK = [
	("div",{"class":"storycontent","id":"storycontent"},"CAPTURETAGS","CAPTUREDATA")
	]

def build_parser():
	parser = argparse.ArgumentParser(description="Convert a FanFiction.net story to a .mobi file for Kindle.")
	parser.add_argument('url', metavar='URL', type=str, help="A FanFiction.net story URL")
	return parser

def what_I_was_doing_before():
	titleparser = HierarchyParser(TITLE_STACK)
	titleparser._doprint = True
	titleparser._printcount = 30
	titleparser.feed(mobile_data)
	print()
	print("Title:",titleparser.data()[:5],"(",len(titleparser.data()),")")
	print()

	with open('sanitized.htm','w') as f:
		f.write(mobile_data)

	authorparser = HierarchyParser(AUTHOR_STACK)
	# authorparser._doprint = True
	# authorparser._printcount = 10
	authorparser.feed(mobile_data)
	print()
	print("Author:",authorparser.data()[:5],"(",len(authorparser.data()),")")
	print()

	tocparser = HierarchyParser(TOC_STACK)
	# tocparser._doprint = True
	# tocparser._printcount = 50
	tocparser.feed(full_data)
	# with open('sanitized.htm','w') as f:
		# f.write(full_data)
	print()
	# print("TOC:",sorted(set(tocparser.data())))
	print("Number of chapters:",len(set(tocparser.data())))
	print()

	textparser = HierarchyParser(CHAPTERTEXT_STACK)
	textparser.feed(mobile_data)
	print()
	print("text:","".join(textparser.data())[:10],"......","".join(textparser.data())[-10:])
	print()

if __name__ == "__main__":
	# parser = build_parser()
	# args = parser.parse_args()
	# url = args.url
	# if "fanfiction.net" not in url.lower():
		# print("Error:",url,"not a fanfiction.net url")
		# parser.exit()
	what_I_was_doing_before()

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