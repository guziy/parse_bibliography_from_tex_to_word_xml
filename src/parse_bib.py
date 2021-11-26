from pathlib import Path
import logging
import re

from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from xml.dom import expatbuilder
from string import ascii_lowercase
from typing import List


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

AUTHOR_INFO = r"\\bibinfo\{author\}\{(.*?)\}"
YEAR_INFO = r"\\bibinfo\{year\}\{(\d+).*?\}"
TITLE_INFO = r"\\bibinfo\{title\}\{(.*?)\}"
JOURNAL_INFO = r"\\bibinfo\{journal\}\{(.*?)\}"
VOLUME_INFO = r"\\bibinfo\{volume\}\{(.*?)\}"
PAGES_INFO = r"\\bibinfo\{pages\}\{(.*?)\}"
URL_INFO = r"\\bibinfo\{url\}\{(.*?)\}"
ADDRESS_INFO = r"\\bibinfo\{address\}\{(.*?)\}"
TYPE_INFO = r"\\bibinfo\{type\}\{(.*?)\}"
INST_INFO = [r"\\bibinfo\{school\}\{(.*?)\}", r"\\bibinfo\{organization\}\{(.*?)\}"]
DOI_INFO = r"\\doi\{(.*?)\}"


tags = []
tag_extensions = [""] + [c for c in ascii_lowercase]


class Author(object):
    def __init__(self, first_name="", last_name="", middle_name=""):
        self.first_name = first_name
        self.last_name = last_name
        self.middle_name = middle_name

    def extract_name_parts(self, s):
        logger.debug(s)
        parts = s.split(",")
        self.last_name = parts[0].strip()

        if len(parts) > 1:
            names = parts[1].strip().split(".")

            self.first_name = names[0]

            if len(names) > 1:
                self.middle_name = names[1]

    def __str__(self):
        rep = f"{self.last_name}"

        if len(self.first_name) > 0:
            rep = f"{rep}, {self.first_name}."

        if len(self.middle_name) > 0:
            rep = f"{rep}{self.middle_name}."

        return rep

    def to_word_xml(self):

        person = Element("b:Person")

        last_name_el = SubElement(person, "b:Last")
        first_name_el = SubElement(person, "b:First")
        middle_name_el = SubElement(person, "b:Middle")

        last_name_el.text = self.last_name
        first_name_el.text = f"{self.first_name}." if len(self.first_name) == 1 else self.first_name

        if len(self.middle_name) > 0:
            middle_name_el.text = f"{self.middle_name}." if len(self.middle_name) == 1 else self.middle_name

        return person


class BibItem(object):
    def __init__(self):
        self.key = ""
        self.guid = ""
        self.title = ""
        self.authors = []
        self.year = ""
        self.journal = ""
        self.volume = ""
        self.pages = ""
        self.url = ""
        self.address = ""
        self.doi = ""
        self.type = ""
        self.institution = ""
        self._tag = ""
        self.book_title = ""
        self.publisher = ""

    def get_tag(self):

        if len(self._tag) > 0:
            return self._tag

        a = self.authors[0].last_name
        tag = a[:min(3, len(a))] + self.year[-2:]

        for ext in tag_extensions:
            if tag + ext not in tags:
                self._tag = tag + ext
                tags.append(self._tag)
                break

        return self._tag

    def __str__(self):
        s = ", ".join([str(a) for a in self.authors]) + f" ({self.year}): {self.title}"

        if len(self.doi) > 0:
            s = f"{s}, doi:{self.doi}"

        s = f"(id={self.get_tag()})-->{s}"

        return s

    def to_bibtex(self) -> dict:
        """Convert to bibtex fomat
        """
        the_id = self.authors[0].last_name
        the_id = f"{the_id}:{self.year}"

        the_authors = " and ".join([
            str(a) for a in self.authors
        ])

        bib_dict = {
            "ID": the_id, 
            "year": self.year, 
            "author": the_authors,
            "title": self.title,
            "journal": self.journal,
            "pages": self.pages,
            "city": self.address,
            "doi": self.doi,
            "volume": self.volume,
            "institution": self.institution,
            "publisher": self.publisher,
            "url": self.url,
            "ENTRYTYPE": self.get_reference_type()
        }
        return bib_dict


    
    def get_reference_type(self):
        """Type of the reference journal article or else
        """
        if len(self.journal) > 0:
            return "article"
        elif len(self.book_title) > 0 and len(self.title) > 0:
            return "book"
        else:
            return "report"


    def to_word_xml(self):
        el = Element("b:Source")

        y_el = SubElement(el, "b:Year")
        y_el.text = self.year

        author = SubElement(el, "b:Author")
        author = SubElement(author, "b:Author")

        nl = SubElement(author, "b:NameList")
        nl.extend([a.to_word_xml() for a in self.authors])

        title_el = SubElement(el, "b:Title")
        title_el.text = self.title

        if len(self.journal) > 0:
            journal_el = SubElement(el, "b:JournalName")
            journal_el.text = self.journal

        if len(self.pages) > 0:
            pages_el = SubElement(el, "b:Pages")
            pages_el.text = self.pages

        city_el = SubElement(el, "b:City")
        city_el.text = self.address

        if len(self.url) > 0:
            url_el = SubElement(el, "b:URL")
            url_el.text = self.url

        type_el = SubElement(el, "b:SourceType")
        if len(self.journal) > 0:
            type_el.text = "JournalArticle"
        elif len(self.book_title) > 0 and len(self.title) > 0:
            type_el.text = "BookSection"
        else:
            type_el.text = "Report"

        thesis_type = SubElement(el, "b:ThesisType")
        thesis_type.text = self.type

        if len(self.institution) > 0:
            inst = SubElement(el, "b:Institution")
            inst.text = self.institution

        tag_el = SubElement(el, "b:Tag")
        tag_el.text = self.get_tag()

        if len(self.volume) > 0:
            volume_el = SubElement(el, "b:Volume")
            volume_el.text = self.volume

        if len(self.doi) > 0:
            doi_el = SubElement(el, "b:DOI")
            doi_el.text = self.doi

        if len(self.book_title) > 0:
            book_title_el = SubElement(el, "b:BookTitle")
            book_title_el.text = self.book_title

        # try to copy publisher from other fields
        if len(self.publisher) == 0:
            self.publisher = self.institution

        publisher_el = SubElement(el, "b:Publisher")
        publisher_el.text = self.publisher

        return el


def get_authors(line):
    return get_value(line, token_id="author")


def get_value(line: str, token_id: str = "author"):
    res = []

    pattern = re.compile(r"\\bibinfo\s*{\bs*" + token_id + r"\b\s*}")

    match = pattern.search(line)

    if match is None:
        return res

    # check if it is a real bibinfo

    while True:

        usable_data = []
        open_count = 0
        first_bracket = line.index(r"{", match.end())
        open_count += 1

        for i in range(first_bracket + 1, len(line)):
            if line[i] == r"}":
                open_count -= 1
            elif line[i] == r"{":
                open_count += 1

            assert open_count >= 0, r"Unbalanced brackets {, }"

            if open_count == 0:
                break

            if line[i] not in ["{", "}"]:
                usable_data.append(line[i])

        res.append("".join(usable_data))

        match = pattern.search(line, first_bracket)
        if match is None:
            break

    return res


def parse_bibitem(lines):
    if len(lines) == 0:
        return None

    bib = BibItem()
    s = " ".join(lines)
    s = clean(s)

    # logger.debug(lines)

    for gr in get_authors(s):
        a = Author()
        a.extract_name_parts(gr)
        bib.authors.append(a)

    for gr in get_value(s, "year"):
        bib.year = gr
        break

    for gr in get_value(s, "title"):
        bib.title = gr

    for gr in re.findall(JOURNAL_INFO, s):
        bib.journal = gr

    for gr in re.findall(VOLUME_INFO, s):
        bib.volume = gr

    for gr in get_value(s, "pages"):
        bib.pages = gr

    for gr in re.findall(URL_INFO, s):
        bib.url = gr.replace(r"\url{", "")

    for gr in re.findall(ADDRESS_INFO, s):
        if "http:" in gr:
            bib.url = gr.replace(r"\url{", "")
        else:
            bib.address = gr

    for gr in re.findall(TYPE_INFO, s):
        bib.type = gr

    for pattern in INST_INFO:
        for gr in re.findall(pattern, s):
            bib.institution = gr

    for gr in re.findall(DOI_INFO, s):
        bib.doi = gr

    for gr in get_value(s, "booktitle"):
        bib.book_title = gr

    for gr in get_value(s, "publisher"):
        bib.publisher = gr

    logger.debug(bib)

    if len(bib.authors) == 0:
        logger.error([str(bib), "does not have authors"])

    return bib


def clean(line):
    line = line.strip().replace("~", " ")
    line = line.replace(r"\`{e}", "è")
    line = line.replace(r"\'{c}", "\u0107").replace(r"\^{o}", "ô").replace(r"\'{e}", "é")
    # line = line.replace(r"{GEM}", "GEM").replace(r"{IPSL}", "IPSL").replace(r"{GDPS}", "GDPS")
    # line = line.replace(r"{(GEM)}", "GEM")
    # line = line.replace(r"{GEPS}", "GEPS")
    # line = line.replace(r"{US}", "US").replace(r"{UK}", "UK")
    line = line.replace(r"\"{a}", "ä")

    # line = line.replace(r"{RDPS}", "RDPS")
    # line = line.replace(r"{MATLAB}", "MATLAB")
    line = line.replace(r"\ ", " ").replace(r"{TIDE}", "TIDE").replace(r"$\_$", "_")
    # line = line.replace(r"{CMC-MRB}", "CMC-MRB")

    single_letters = re.findall(r"\{(\w)\}", line)
    for sl in single_letters:
        line = line.replace(f"{{{sl}}}", sl)

    return line


def parse_citations(fpath: Path) -> List[BibItem]:
    """
    :param fpath: path to the initial file containing citations in tex format
    :rtype: List[BibItem]
    """

    bibs = []
    cur_lines = []
    with fpath.open() as f:
        for line in f:

            line = line.strip()

            if line.startswith("%") or line == "":
                continue

            if line.lower().startswith(r"\bibitem"):

                if len(cur_lines) > 0:
                    bibs.append(parse_bibitem(cur_lines))

                cur_lines = [line, ]
            else:
                cur_lines.append(line)

    bib = parse_bibitem(cur_lines)

    if bib is not None:
        bibs.append(bib)

    return bibs


def main_rdsps():
    in_file = Path("data/rdsps_citations.txt")
    bibs = parse_citations(in_file)

    ET.register_namespace("xlmns:b", "http://schemas.openxmlformats.org/officeDocument/2006/bibliography")
    top = Element("b:Sources")
    top.extend([b.to_word_xml() for b in bibs])

    xml_str = expatbuilder.parseString(tostring(top), False).toprettyxml()
    with open("rdsps.xml", "w") as f:
        f.write(xml_str)


def main_resps():
    in_file = Path("data/resps_citations.txt")
    bibs = parse_citations(in_file)

    ET.register_namespace("xlmns:b", "http://schemas.openxmlformats.org/officeDocument/2006/bibliography")
    top = Element("b:Sources")
    top.extend([b.to_word_xml() for b in bibs])

    xml_str = expatbuilder.parseString(tostring(top), False).toprettyxml()
    with open("resps.xml", "w") as f:
        f.write(xml_str)


if __name__ == '__main__':
    main_resps()
