# Adapted from the csv.writer example in the Python documentation (PSF License).
# This is the original 2018 learning exercise, ported to Python 3.
import csv
from pathlib import Path

EXAMPLE_ROWS = (
    ["Spam"] * 5 + ["Baked Beans"],
    ["Spam", "Lovely Spam", "Wonderful Spam"],
)


def write_example(path: Path) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(
            handle, delimiter=" ", quotechar="|", quoting=csv.QUOTE_MINIMAL, lineterminator="\n"
        )
        writer.writerows(EXAMPLE_ROWS)
