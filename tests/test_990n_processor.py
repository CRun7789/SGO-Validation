import os
import importlib

# Import module with numeric name
processor = importlib.import_module("src.utils.990n_processor")


SAMPLE = """
000981374|2009|THE FALMOUTH WALK INC|T|F|01-01-2009|12-31-2009|www.falmouthwalk.org|WILLIAM MCCABE|50 SURREY LN||EAST FALMOUTH||MA|02536|US|50 SURREY LANE||EAST FALMOUTH||MA|02536|US|||
123456789|2010|ANOTHER ORG|T|F|01-01-2010|12-31-2010||CONTACT|ADDR|||||||
"""


def write_sample(path: str):
    with open(path, "w", encoding="ascii") as fh:
        fh.write(SAMPLE.strip() + "\n")


def test_load_and_lookup(tmp_path):
    p = tmp_path / "sample_epostcard.txt"
    write_sample(str(p))

    # Set the global filepath before calling functions
    processor._EPOSTCARD_FILEPATH = str(p)

    mapping = processor.load_ein_website_map()
    assert mapping.get("000981374") == "www.falmouthwalk.org"
    assert mapping.get("123456789") is None

    # Test get_website_by_ein with different EIN formats
    assert processor.get_website_by_ein("000981374") == "www.falmouthwalk.org"
    assert processor.get_website_by_ein("981374") == "www.falmouthwalk.org"

    # Test website/status lookup behavior
    assert processor.get_website_with_status("000981374", None) == "www.falmouthwalk.org"
    assert processor.get_website_with_status("000981374", "Another Org") == "www.falmouthwalk.org"
    assert processor.get_website_with_status("123456789", None) == None
    assert processor.get_website_with_status(None, "Another Org") == None
    assert processor.get_website_with_status("000000000", "Unknown Org") == None
    assert processor.get_website("123456789", None) is None
