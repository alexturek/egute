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

class FanFictionHtmlParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
	def handle_starttag(self, tag, attrs):
		print("Encountered a start tag:", tag, attrs)
	def handle_endtag(self, tag):
		print("Encountered an end tag :", tag)
	def handle_data(self, data):
		print("Encountered some data  :", data)
	def publisher(self):
		return "fanfiction.net"

def clamp(min, val, max):
	return sorted((min, val, max))[1]

def mapify(list_of_pairs):
	return {k:v for k,v in list_of_pairs}

def entirely_contains(superset, subset):
	return all(item in superset.items() for item in subset.items())

class HierarchyParser(HTMLParser):
	def __init__(self, tag_stack, data_bucket):
		HTMLParser.__init__(self)
		self._stack_state = -1
		self._stack = tag_stack
	def handle_starttag(self, tag, attrs):
		self._stack_state = self._move_stack(tag.lower(), attrs, self._stack_state, self._stack)
		self._get_frame().handle_starttag(tag,attrs)
	def handle_data(self, data):
		if self._ignore_more_data():
			return
		if self._in_text_capture_frame():
			self._data.append(data.strip())
	def handle_endtag(self, tag):
		if self._stack_state >= 0 and self._catch_multiple:
			self._stack_state = self._stack_state - 1
	def data(self):
		return self._data
	def _ignore_more_data(self):
		return not (len(self._data) == 0 or self._catch_multiple)
	def _in_text_capture_frame(self):
		stack_index = clamp(0, self._stack_state, len(self._stack) - 1)
		closest_frame = self._stack[stack_index]
		return "CAPTUREDATA" in closest_frame
	def _move_stack(self, tag, attrs, state, stack):
		"""
		Return a new state value if the current tag+attrs match where we need to be in our stack
		"""
		if state >= len(stack) - 1:
			return state
		search_frame = stack[state + 1]
		if search_frame[0] != tag:
			return state
		test_attrs = search_frame[1]
		if not all(item in attrs.items() for item in test_attrs.items()):
			return state
		print("incrementing state to", state+1, search_frame)
		return state + 1

class DataBucket(object):
	def handle_starttag(self, tag, attrs):
		pass
	def handle_data(self, data):
		pass
	def handle_endtag(self, tag):
		pass
	def data(self):
		return []

class TextOnlyBucket(DataBucket):
	def __init__(self):
		self._data = []
	def handle_data(self, data):
		self._data.append(data)
	def data(self):
		return self._data

class StackFrame:
	def __init__(self, tagname, required_attrs={}, data_bucket=DataBucket()):
		self._tagname = tagname
		self._required_attrs = required_attrs
		self._data_bucket = data_bucket
		self._depth = 0
	def handle_starttag(self, tag, attrs):
		""" return True if this stack frame can handle this tag/attrs, False if you should shift up a frame """
		attrs = mapify(attrs)
		attrs_match = entirely_contains(attrs, self._required_attrs)
		if tag == self._tagname and attrs_match or self._depth > 0:
			self._depth = self._depth + 1
			self._data_bucket.handle_starttag(tag, attrs)
			return True
		return False
	def handle_data(self, data):
		self._data_bucket.handle_data(data)
	def handle_endtag(self, tag):
		""" return True if this stack frame can still handle this tag, False if you should shift down a frame """
		pass

# for m.fanfiction.net
# <div style='padding:5px 10px 5px 10px;' class='storycontent' id='storycontent' ><p>Disclaimer: J. K. Rowling owns Harry Potter
class ChapterTextParser(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self._stack = []
	def tag_starts(tag, attrs):
		return False
	def handle_starttag(self, tag, attrs):
		pass
	def handle_endtag(self, tag):
		pass
	def handle_data(self, data):
		pass
	def chaptertext(self):
		"""
		Return the body text from the chapter just parsed
		"""
		return self._chapter_text

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
		("div",{"class":"storycontent","id":"storycontent"},"CAPTUREALL")
		]
		
	titleparser = HierarchyParser(TITLE_STACK)
	# titleparser.feed(mobile_data)
	# print("Title:",titleparser.data())

	authorparser = HierarchyParser(AUTHOR_STACK)
	# authorparser.feed(mobile_data)
	# print("Author:",authorparser.data())

	tocparser = HierarchyParser(TOC_STACK,True)
	# tocparser.feed(full_data)
	# print("TOC:",tocparser.data())

	textparser = HierarchyParser(CHAPTERTEXT_STACK,True)
	textparser.feed(full_data)
	print("chapter text:",textparser.data())
	

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