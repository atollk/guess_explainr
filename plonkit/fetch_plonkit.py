import contextlib
import datetime
import json
import os
import sys

import tqdm
from image_compress import compress as compress_image  # pyrefly: ignore[missing-import]
from plonkit_countries import Country, fetch_countries  # pyrefly: ignore[missing-import]
from plonkit_pdf import fetch_country_guide_pdf  # pyrefly: ignore[missing-import]
from tqdm.contrib import DummyTqdmFile


@contextlib.contextmanager
def _std_out_err_redirect_tqdm():
    orig_out_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = map(DummyTqdmFile, orig_out_err)
        yield orig_out_err[0]
    # Relay exceptions
    except Exception as exc:
        raise exc
    # Always restore sys.stdout/err if necessary
    finally:
        sys.stdout, sys.stderr = orig_out_err


def main():
    countries = fetch_countries()
    dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(dir, exist_ok=True)

    metadata_path = os.path.join(dir, "metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            metadata = json.load(f)
    else:
        metadata = {}

    with _std_out_err_redirect_tqdm() as original_stdout:
        for i, country in tqdm.tqdm(enumerate(countries), file=original_stdout):
            assert isinstance(country, Country)
            print(f"{i + 1} / {len(countries)} : {country.slug}")
            pdf_path: str = os.path.join(dir, f"{country.slug}.pdf")

            last_pull = None
            if country.slug in metadata:
                m = metadata[country.slug]
                if "last_update" in m:
                    last_pull = datetime.date.fromisoformat(m["last_update"])

            last_update = country.last_updated.date()
            requires_update = last_pull is None or last_update >= last_pull
            if not os.path.exists(pdf_path) or requires_update:
                fetch_country_guide_pdf(country.slug, pdf_path, image_transform=compress_image)
                metadata[country.slug] = {"last_update": datetime.date.today().isoformat()}
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f)
            else:
                print("Skipping because it already exists and there is no recent update.")


if __name__ == "__main__":
    main()
