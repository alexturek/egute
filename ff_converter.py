import re
import os
import sys
import argparse
import codecs
import time
import shutil
from urllib.request import urlopen
from bs4 import BeautifulSoup

# hp_url = 'http://www.fanfiction.net/s/5782108/1/Harry-Potter-and-the-Methods-of-Rationality'

def write_to_file(filename, text):
	if len(filename) > 200:
		raise ValueError("filename")
	with codecs.open(filename, 'w', 'utf-8-sig') as outputfile:
		print(text, file=outputfile)
def read_from_file(filename):
	with open(filename) as file:
		return file.read()
def build_arg_parser():
   parser = argparse.ArgumentParser(description="Convert a FanFiction.net story to a .mobi file for Kindle.")
   parser.add_argument('url', metavar='URL', type=str, help="A FanFiction.net story URL")
   return parser
def sanitize_chapter_title(title_with_number):
	return re.match('\d+\.\s+(.+)', title_with_number).groups()[0]
def get_ff_story_chapter_names(html_content):
	chapter_numbers = [int(option["value"]) for option in html_content.find(id='chap_select').find_all('option')]
	chapter_names = [sanitize_chapter_title(option.contents[0]) for option in html_content.find(id='chap_select').find_all('option')]
	return sorted(zip(chapter_numbers, chapter_names))
url_regex = "https?://www.fanfiction.net/[^\/]/\\d+/"
def get_chapter_url(url, chapter_num):
	return re.search(url_regex, url).group() + str(chapter_num)
def get_ff_story_chapter_html(html_content):
	return html_content.find(id="storytext")
def get_ff_story_title(html):
	return html.find(id='content_wrapper_inner').table.tr.td.b.string
def get_ff_story_author(html):
	return html.find(id='content_wrapper_inner').table.tr.td.a.string
def get_ff_story_description(html):
	return html.find(id='content_wrapper_inner').table.tr.td.select('div.xcontrast_txt')[0].string
def make_chapter_html(chapter_title, chapter_html):
	html = BeautifulSoup("<html><body><h1 id='chapter_title'/></body></html>")
	html.find(id='chapter_title').string = chapter_title
	html.body.append(chapter_html)
	return html
def chapter_link(num):
	return "chapter-{}.html".format(num)
def make_toc_html(title, author, chapters):
	html = BeautifulSoup("<html><body><h1 id='title'/><h2 id='author'/></body></html>")
	html.find(id='title').string = title
	html.find(id='author').string = author
	chapter_list = html.new_tag('ol')
	html.find(id='author').append(chapter_list)
	for chapter_num, chapter_title in chapters:
		list_item = html.new_tag("li")
		link = html.new_tag("a", href=chapter_link(chapter_num))
		link.string = chapter_title
		list_item.append(link)
		chapter_list.append(list_item)
	return html
opf_template = read_from_file('book.opf.template')
def make_book_opf(title, author, chapters, description, publisher):
	chapter_manifest_list = make_chapter_manifest_list(chapters)
	spine_refs = make_spine_refs(chapters)
	guide_refs = make_guide_refs(chapters)
	return opf_template.format(
		title=title,
		author=author,
		description=description,
		publisher=publisher,
		chapter_manifest_list=chapter_manifest_list,
		spine_refs=spine_refs,
		guide_refs=guide_refs)
chapter_manifest_template = '<item id="{id}" href="{url}" media-type="application/xhtml+xml" />'
def make_chapter_manifest_list(chapters):
	manifests = []
	for chapter_num, chapter_title in chapters:
		url = chapter_link(chapter_num)
		id = 'c' + str(chapter_num)
		manifests.append(chapter_manifest_template.format(id=id, url=url))
	return '\n'.join(manifests)
spine_ref_template = '<itemref idref="c{chapter_num}" />'
def make_spine_refs(chapters):
	return '\n'.join([spine_ref_template.format(chapter_num=chapter_num) for chapter_num, chapter_title in chapters])
guide_ref_template = '<reference type="text" title="{chapter_title}" href="{url}" />'
def make_guide_refs(chapters):
	return '\n'.join([guide_ref_template.format(chapter_title=chapter_title, url=chapter_link(chapter_num)) for chapter_num, chapter_title in chapters])
ncx_template = read_from_file('toc.ncx.template')
def make_toc_ncx(title, author, chapters):
	navmap = make_ncx_navmap(chapters)
	return ncx_template.format(title=title, author=author, navmap=navmap)
def make_ncx_navmap(chapters):
	return make_ncx_toc() + '\n'.join([make_ncx_chapter(number, title) for number,title in chapters])
def make_ncx_toc():
	return make_ncx_navpoint(1, "Table of Contents", 'toc.html')
def make_ncx_chapter(number, title):
	return make_ncx_navpoint(number+1, title, chapter_link(number))
def make_ncx_navpoint(number, title, html_name):
	return '\n'.join((
		'',
		'	<navPoint id="navpoint-%d" playOrder="%d">' % (number,number),
		'		<navLabel>',
		'			<text>%s</text>' % title,
		'		</navLabel>',
		'		<content src="%s"/>' % html_name,
		'	</navPoint>'))
def generate_chapter_html_files(tempdir, url, chapters):
	for number, title in chapters:
		html = BeautifulSoup(urlopen(get_chapter_url(url, number)))
		content = get_ff_story_chapter_html(html)
		chapter_file_name = tempdir + chapter_link(number)
		chapter_file_html = make_chapter_html(title, content)
		write_to_file(chapter_file_name, chapter_file_html)
def make_tempdir():
	timestamp = str(time.time()).replace('.','')
	tempdir = os.sep.join((os.getcwd(), "kindletmp_" + str(timestamp), ''))
	os.makedirs(tempdir)
	return tempdir
def delete_dir(tempdir):
	if tempdir.split(os.sep)[-2].startswith('kindletmp_'):
		shutil.rmtree(tempdir.replace(os.sep, '/'))
	else:
		print("---------------------------------------")
		print("WARNING: Trying to delete " + tempdir)
		print("---------------------------------------")
		sys.exit()
if __name__ == "__main__":
	parser = build_arg_parser()
	args = parser.parse_args()
	url = args.url
	if "fanfiction.net" not in url.lower():
		print("Error:",url,"is not a fanfiction.net url")
		parser.exit()

	sample_data = urlopen(url).readall()
	html = BeautifulSoup(sample_data)
	chapters = get_ff_story_chapter_names(html)
	title = get_ff_story_title(html)
	author = get_ff_story_author(html)
	description = get_ff_story_description(html)
	publisher = "FanFiction.net"

	tempdir = make_tempdir()

	generate_chapter_html_files(tempdir, url, chapters)
	write_to_file(tempdir + 'toc.html', make_toc_html(title, author, chapters))
	write_to_file(tempdir + 'toc.ncx', make_toc_ncx(title, author, chapters))
	write_to_file(tempdir + 'book.opf', make_book_opf(title, author, chapters, description, publisher))

	os.system('kindlegen\kindlegen.exe ' + tempdir + 'book.opf -o book.mobi')
	shutil.copyfile(tempdir + 'book.mobi', 'book.mobi')
	
	delete_dir(tempdir)

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