import csv


def load(path):
    with open(path, newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]
