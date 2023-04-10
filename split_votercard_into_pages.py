import argparse
import csv
from collections import defaultdict


def main():
    parser = argparse.ArgumentParser(
        description = "Figures out which columns are on which pages")
    parser.add_argument("-i", "--input-csv-filename", default="voter_cards.csv")
    parser.add_argument("-o", "--output-csv-filename-pattern",
                        default="voter_cards.%d.csv")
    args = parser.parse_args()

    sets = {} # column -> set
    header = None
    rows = []

    # at the end of this block:
    # - sets will contain a mapping of column -> set of columns on that page
    # - header will be the header row
    # - rows will contain all the data rows
    with open(args.input_csv_filename, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            rows.append(row)

            # start with 1 to skip precinct
            keys = [header[i] for i in range(1, len(row)) if row[i] != '']

            s = set(keys)

            for k in keys:
                if k in sets:
                    s.update(sets[k])
            for k in keys:
                sets[k] = s

    unique_sets = set(tuple(sorted(s)) for s in sets.values())

    header_index = {v:i for i, v in enumerate(header)}

    sorted_sets = sorted(unique_sets, key=lambda x: header_index[x[0]])

    def find_set_index(r):
        """for a row of data (r), returns the index of its set in sorted_sets"""
        r = r[1:]  # remove precinct
        for i, x in enumerate(r):
            if x != "":
                for j, s in enumerate(sorted_sets):
                    if header[i+1] in s:
                        return j

                assert False, r


    sorted_page_headers = [["precinct"] + sorted(s, key=lambda x: header_index[x]) for s in sorted_sets]
    page_data = [[] for _ in range(len(sorted_page_headers))]

    for r in rows:
        set_index = find_set_index(r)
        truncated_data = []
        for h in sorted_page_headers[set_index]:
            hindex = header_index[h]
            truncated_data.append(r[hindex])

        assert len(truncated_data) == len(sorted_page_headers[set_index])
        page_data[set_index].append(truncated_data)

    for i, ph in enumerate(sorted_page_headers):
        with open(args.output_csv_filename_pattern % (i + 1), "w") as f:
            writer = csv.writer(f)
            writer.writerow(ph)
            for r in page_data[i]:
                writer.writerow(r)


if __name__ == "__main__":
    main()
