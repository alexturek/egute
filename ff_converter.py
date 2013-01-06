import re
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
		self._original_url = url
		self._has_cached_data = False
		self._chapters = []
		self._url_split = list(urlparse(last))
		path = self._url_split[2]
		self._path_parts = re.search(FanfictionNetStory._path_search_regex, lastpath).groupdict()
		self.htmlparser = FanFictionHtmlParser()
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
		self._verify_cached()
		return self.htmlparser.publisher()
	def _verify_cached(self):
		if self._has_cached_data:	
			return
		self._has_cached_data = True
		resp = urlopen(self._original_url).readall()
		self.htmlparser.feed(resp)
		self._story_title = self.htmlparser.story_title()
		for chapter_index,chapter_title in enumerate(self.htmlparser.table_of_contents()):
			self._chapters.append(FanFictionNetChapter(chapter_index, chapter_title, self._make_chapter_url(chapter_index)))

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

class HierarchyParser(HTMLParser):
	def __init__(self, tag_stack):
		HTMLParser.__init__(self)
		self._stack = tag_stack
		self._capture_state = -1
		self._data = []
	def handle_starttag(self, tag, attrs):
		self._incr_tag()
		self._enter_capture_state(tag.lower(), attrs)
		self._capture_tag(tag, attrs)
	def handle_endtag(self, tag):
		self._decr_tag()
		self._capture_endtag(tag)
	def _enter_capture_state(self, tag, attrs):
		if self._capture_state < 0 and self._matches(tag, attrs, self._stack[0]):
			self._capture_state = 0
	def _capture_tag(self, tag, attrs):
		if self._in_tag_capture_frame():
			if self._handle_special_cases(tag, attrs):
				return
			attrs_list = attrs_to_str(attrs)
			html = ''.join(("<", tag, attrs_list, ">"))
			self._data.append(html)
	def _capture_endtag(self, tag):
		if self._in_tag_capture_frame():
			html = ''.join(("</", tag, ">"))
			self._data.append(html)
	def _handle_special_cases(self, tag, attrs):
		if tag.lower() == 'br':
			self._data.append('<br/>')
			self._decr_tag()
			return True
		elif tag.lower() == 'hr':
			self._data.append(''.join(("<", tag, attrs_to_str(attrs), "/>")))
			self._decr_tag()
			return True
		return False
	def _incr_tag(self):
		if self._capture_state >= 0:
			self._capture_state = self._capture_state + 1
	def _decr_tag(self):
		self._capture_state = clamp(-1, self._capture_state - 1, self._capture_state)
	def _get_capture_frame(self):
		'''Return None if we aren't in a capture state; otherwise return the current capture frame'''
		idx = clamp(-1, self._capture_state, len(self._stack) - 1)
		if idx < 0:
			return None
		return self._stack[idx]
	def handle_data(self, data):
		if self._in_text_capture_frame():
			self._data.append(data.strip())
	def data(self):
		return self._data
	def _in_text_capture_frame(self):
		closest_frame = self._get_capture_frame()
		return None != closest_frame and "CAPTUREDATA" in closest_frame
	def _in_tag_capture_frame(self):
		closest_frame = self._get_capture_frame()
		return None != closest_frame and "CAPTURETAGS" in closest_frame
	def _matches(self, tag, attrs, search_frame):
		'''Return True/False if the tag/attrs matches this stack frame'''
		attrs = mapify_attrs(attrs)
		if search_frame[0] != tag:
			return False
		test_attrs = search_frame[1]
		if not all(item in attrs.items() for item in test_attrs.items()):
			return False
		return True

# for m.fanfiction.net
# <div style='padding:5px 10px 5px 10px;' class='storycontent' id='storycontent' ><p>Disclaimer: J. K. Rowling owns Harry Potter

hp_url = 'http://www.fanfiction.net/s/5782108/1/Harry-Potter-and-the-Methods-of-Rationality'
m_hp_url = hp_url.replace('www.fanfiction.net', 'm.fanfiction.net')

mobile_data = str(urlopen(m_hp_url).readall())
full_data = str(urlopen(hp_url).readall())

# for m.fanfiction.net:
# <div id=content><center><b>Harry Potter and the Methods of Rationality</b> by <a href='/u/2269863/'>Less Wrong</a></center>

# for www.fanfiction.net
# <SELECT id=chap_select title="Chapter Navigation" Name=chapter onChange="self.location = '/s/5782108/'+ this.options[this.selectedIndex].value + '/Harry-Potter-and-the-Methods-of-Rationality';"><option  value=1 selected>1. A Day of Very Low Probability<option  value=2 >2. Everything I Believe Is False<option  value=3 >3. Comparing Reality To Its Alternatives

if __name__ == "__main__":
	TITLE_STACK = [
		("div",{"id":"content"}),
		("center",{}),
		("b",{}, "CAPTUREDATA")]
	AUTHOR_STACK = [
		("div",{"id":"content"}),
		("center",{}),
		("a",{}, "CAPTUREDATA")]
	TOC_STACK = [
		("select",{"id":"chap_select"}),
		("option",{}, "CAPTUREDATA")
		]
	CHAPTERTEXT_STACK = [
		("div",{"class":"storycontent","id":"storycontent"},"CAPTURETAGS","CAPTUREDATA")
		]
		
	titleparser = HierarchyParser(TITLE_STACK)
	titleparser.feed(mobile_data)
	# print("Title:",titleparser.data())

	authorparser = HierarchyParser(AUTHOR_STACK)
	authorparser.feed(mobile_data)
	# print("Author:",authorparser.data())

	tocparser = HierarchyParser(TOC_STACK)
	tocparser.feed(full_data)
	# print("TOC:",tocparser.data())

	textparser = HierarchyParser(CHAPTERTEXT_STACK)
	textparser.feed(mobile_data)
	# print("text:","".join(textparser.data()))

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