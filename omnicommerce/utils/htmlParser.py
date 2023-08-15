from bs4 import BeautifulSoup

def parseHtmlText(item):
	return BeautifulSoup(item, 'html.parser').get_text() if item else None
