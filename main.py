'''Extracts commumity petitions for Ara.'''
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import List
from urllib.request import urlopen
import argparse
import datetime
import json

YEAR_A=2020
URL_PREFIX='https://www.priestsforlife.org'
ID_FOR_SPANISH_URL='ctl00_ContentPlaceHolder1_FormView1_SPHyperLink'
ID_FOR_SPANISH_PETITIONS='ctl00_ctl00_parent_body_body_FormView1_GeneralIntercessionLabel'
INDEX_URL = 'https://www.priestsforlife.org/liturgy/archive.aspx'
INDEX_FILE='/home/rprs/src/church_community_prayers/index.txt'
ACTION_OPTIONS = [
    'print',
    'update',
    'list',
    ]


@dataclass
class YearIndex:
    '''Entry (one per Sunday) in the list of petitions for the year.'''
    name: str
    url: str
    visited: bool

    def to_string(self):
      return '{0},{1},{2}\n'.format(self.name, self.url, str(self.visited))

    def print(self):
      return '{0} {1} - {2}'.format('X' if self.visited else '0', self.name, self.url)


@dataclass
class Petitions:
    '''Holds the petitions for a Sunday'''
    introduction: str
    conclusion: str
    petitions: List[str] = field(default_factory=list)

    def to_string(self, language='en'):
      '''Prints the whole document for the specific peititons.'''
      celebrant = {
          'en': 'Celebrant\n',
          'es': 'Celebrante\n',
      }
      lector = {
          'en': 'Deacon/Lector\n',
          'es': 'Diácono/Lector\n',
      }
      text = ''
      text += celebrant[language]
      text += '\n'
      text += self.introduction
      text += '\n\n'
      text += lector[language]
      text += '\n'
      text += self.petitions_to_string()
      text += '\n'
      text += celebrant[language]
      text += '\n'
      text += self.conclusion
      return text

    def petitions_to_string(self):
      ''' Prints the petition array in the format for the doc.'''
      text = ''
      index = 0
      letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'
      for p in self.petitions:
        text += letters[index]
        text += '\n'
        text += p
        text += '\n'
        index += 1
      return text

def write_index_file(index):
    '''Writes list of YearIndex objects to a file.'''
    with open(INDEX_FILE, 'w') as f:
      for i in index:
        f.write(i.to_string())

def read_index_file():
    '''Reads the index file and returns list of YearIndex objects.'''
    with open(INDEX_FILE, 'r') as f:
      file_content = f.readlines()
    index = []
    for line in file_content:
        if line is not None:
            l = line[:-1].split(',')
            index.append(YearIndex(l[0], l[1], l[2] == 'True'))
    return index

def get_initial_index():
    '''Gets the list of urls for the community petitions on every day of the year.'''
    page = get_soup(INDEX_URL)
    body_tag = page.find_all('div', class_='panel-body').pop()
    year_cycles = body_tag.find_all('div', class_='col-md-4')
    curent_year_cycle = (datetime.datetime.now().year - YEAR_A) % 3
    links = year_cycles[curent_year_cycle].find_all('a')
    return [YearIndex(l.contents[0], l['href'], False) for l in links]

def write_initial_file():
    write_index_file(get_initial_index())

def get_soup(url):
    '''Returns the beautiful soup of any url.'''
    html = urlopen(url).read()
    return BeautifulSoup(html, 'html5lib')

def get_next_petitions_index(index):
    # Saving this line of code. thought it was really cool how to get the next
    # elemet in a list with this.
    # link_index = read_index_file();
    # return next(i for i in link_index if not i.visited)
    ctr = 0
    max_ctr = len(index)
    done = False
    while not done and ctr < max_ctr:
      if index[ctr].visited:
        ctr += 1
      else:
        done = True
    return ctr

def get_spanish_link(soup):
    test = soup.find(id=ID_FOR_SPANISH_URL)
    return URL_PREFIX + test['href']

def petitions_in_english(soup):
    ''' Retrieves the petitions from a specific day url.'''
    sections = soup.find_all('div', class_='col-md-12 mb-2')
    section = sections[0]
    pets = section.find_all('p')
    first_index = 0
    # This while loop is to avoid special notes added before the petition, but
    # included in the list of paragraphs. See 
    # https://www.priestsforlife.org/liturgy/liturgicalresource-cycles.aspx?id=172
    # for an example.
    while len(pets[first_index].contents) < 2:
        first_index += 1
    intro = pets[first_index].contents[1]
    petitions = [p.text for p in pets[first_index:-1] if p.contents[0].name != 'strong']
    petitions.append('For those celebrating their birthdays, , we pray to the Lord…')
    conclusion = pets[-1].text
    sanitized_intro = intro.replace(': ', '', 1).strip() if intro.startswith(': ') else intro.strip()
    return Petitions(sanitized_intro, conclusion, petitions)
  
def petitions_in_spanish(soup):
    sections = soup.find(id=ID_FOR_SPANISH_PETITIONS)
    intro = ''
    petitions = []
    conclusion = ''
    strong_ctr = 0
    for s in sections:
      if strong_ctr == 0:
        intro = s.contents[1]
      if s.contents[0].name == 'strong':
        strong_ctr += 1
        if strong_ctr == 2:
          continue
      if strong_ctr == 2 and s.text.strip() is not '':
        petitions.append(s.text)
      if strong_ctr == 3:
        conclusion += s.text
    sanitized_conclusion = conclusion.replace('Celebrante:','').strip()
    sanitized_intro = intro.replace(': ', '', 1).strip() if intro.startswith(': ') else intro
    petitions.append('Por todos los que cumplen años, especialmente por , roguemos al Señor…')
    p = Petitions(sanitized_intro, sanitized_conclusion, petitions)
    return p

def petition_text(index_entry):
    soup = get_soup(index_entry.url)

    # get petitions in english
    english_petitions = petitions_in_english(soup)

    # get link for spanish petitions.
    spanish_url = get_spanish_link(soup)

    # get petitions in spanish.
    spanish_soup = get_soup(spanish_url)
    spanish_petitions = petitions_in_spanish(spanish_soup)

    # text
    text = ''
    text += index_entry.name
    text += '\n\n'
    text += index_entry.url
    text += '\n\n'
    text += english_petitions.to_string()
    text += '\n\n'
    text += spanish_url
    text += '\n\n'
    text += spanish_petitions.to_string('es')
    return text

def today_text(entry1, entry2):
    text = ''
    text += datetime.datetime.today().strftime('%Y-%m-%d')
    text += '\n\n'
    text += petition_text(entry1)
    text += '\n\n'
    text += '# Alternative'
    text += '\n\n'
    text += petition_text(entry2)
    return text

def print_index(index):
    for i in index:
      print(i.print())

def update_index(index):
    # Mark first index as visited.
    i = get_next_petitions_index(index)
    index[i].visited = True
    write_index_file(index)
    for i in index:
      print(i.print())

def get_next_petitions(index):
    i = get_next_petitions_index(index)
    text = today_text(index[i], index[i + 1])
    print(text)

def main():
    '''Main function fo the program'''
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'action',
        metavar = 'action',
        help='One of {0}'.format(ACTION_OPTIONS),
        choices=ACTION_OPTIONS)
    args = parser.parse_args()
    action = args.action
    index = read_index_file()
    if action == 'print':
      get_next_petitions(index)
    elif action == 'update':
      update_index(index)
    elif action == 'list':
      print_index(index)

main()
