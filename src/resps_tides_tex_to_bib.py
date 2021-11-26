
from pathlib import Path

from parse_bib import parse_citations

from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from collections import defaultdict
from string import ascii_lowercase

def main_resps():
    in_file = Path("data/resps-perturbed-tides.txt")
    bibs = parse_citations(in_file)

    db = BibDatabase()


    db.entries = [
        bib.to_bibtex() for bib in bibs
    ]

    id_to_count = defaultdict(lambda : 0)
    for entry in db.entries:
        id_to_count[entry["ID"]] += 1

    for the_id, count in id_to_count.items():
        if count > 1:
            for entry in [e for e in db.entries if e["ID"] == the_id]:
                count -= 1
                entry["ID"] += ascii_lowercase[count]
        



    writer = BibTexWriter()
    writer.indent = "    "
    with Path("data/resps-tides-perturbed-refs.bib").open("wb") as ref_file:
        ref_file.write(writer.write(db).encode())


def main():
    main_resps()


if __name__ == "__main__":
    main()
