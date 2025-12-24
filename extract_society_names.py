import re
import json
from PyPDF2 import PdfReader

PDF_PATH = "FinalList_Ward_139.pdf"

# ---- read pages 1–9 ----
reader = PdfReader(PDF_PATH)
raw_text = ""
for i in range(9):
    raw_text += reader.pages[i].extract_text() + "\n"

# ---- trim to starter ----
starter = "पभरग"
start_idx = raw_text.find(starter)
if start_idx != -1:
    raw_text = raw_text[start_idx:]

# ---- regex ----
ENTRY_REGEX = re.compile(
    r"""
    जरदद\s*भरग\s*क\.?\s*(\d+)
    \s*:\s*
    (\d+)
    \s*-\s*
    (.*?)
    (?=जरदद\s*भरग\s*क\.|\Z)
    """,
    re.DOTALL | re.VERBOSE
)

def normalize_society_text(s: str) -> str:
    s = s.replace("\n", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip(" ,.-")

def is_valid_society_text(s: str) -> bool:
    if len(s) < 15:
        return False
    if len(s.split()) <= 2:
        return False
    return True

def canonical(s: str) -> str:
    return re.sub(r"[,\s]+", " ", s).strip()

collectives = {}
collectives_with_subcollective = {}
for m in ENTRY_REGEX.finditer(raw_text):
    collective = m.group(1)
    subcollective = m.group(2)
    society_raw = normalize_society_text(m.group(3))

    if not is_valid_society_text(society_raw):
        continue

    collectives.setdefault(collective, [])
    collectives_with_subcollective.setdefault(collective, [])


    # fuzzy dedupe
    canon = canonical(society_raw)
    if canon not in {canonical(x) for x in collectives[collective]}:
        collectives[collective].append(society_raw)
        if subcollective:
            collectives_with_subcollective[collective].append([subcollective, society_raw])

# ---- save ----
with open("collective_to_societies.json", "w", encoding="utf-8") as f:
    json.dump(collectives, f, ensure_ascii=False, indent=2)
with open("collective_subcollective_to_societies.json", "w", encoding="utf-8") as f:
    json.dump(collectives_with_subcollective, f, ensure_ascii=False, indent=2)

