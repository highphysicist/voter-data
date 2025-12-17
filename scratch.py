import json
import re
def extract_collective_number(collective_header):
    pattern = r'यभदद भभग क\. (\d+)'
    match = re.search(pattern, collective_header)

    if match:
        return match.group(1)

    # Try alternative patterns
    # alt_patterns = [
    #     r'क\.(\d+)',
    #     r'भभग\s*(\d+)'
    # ]
    #
    # for pattern in alt_patterns:
    #     match = re.search(pattern, collective_header)
    #     if match and collective_header.startswith("यभदद"):
    #         return match

    return None

with open("voter_data_master_final_139.json", "r", encoding='utf-8') as f:
    full_file = json.load(f)

headers_json = full_file["headers"]
cards_json = full_file["cards"]
header_to_pages = {}
final_object = {}


for key in headers_json:
    extracted_headers = headers_json[key]
    for header in extracted_headers:
        collective_number = extract_collective_number(header)
        if collective_number:
            print(collective_number)
            header_to_pages[key] = collective_number

final_object["page_assignments"] = header_to_pages
with open("comprehensive_header_mapping.json", "w") as f:
    json.dump(final_object, f)
