# Adapted from the csv.writer example in the Python documentation (PSF License).
# This is the original 2018 learning exercise, ported to Python 3.
import csv
import io
from pathlib import Path

from m15.storage.files import write_text_atomic

EXAMPLE_ROWS = (
    ["Spam"] * 5 + ["Baked Beans"],
    ["Spam", "Lovely Spam", "Wonderful Spam"],
)


def write_example(path: Path) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.writer(
        buffer, delimiter=" ", quotechar="|", quoting=csv.QUOTE_MINIMAL, lineterminator="\n"
    )
    writer.writerows(EXAMPLE_ROWS)
    write_text_atomic(path, buffer.getvalue())
