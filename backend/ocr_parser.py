import os
import re
from typing import List, Dict
from google.cloud import vision


def _load_google_credentials():
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")

    if not credentials_path:
        raise RuntimeError("GOOGLE_CREDENTIALS_PATH not set in environment")

    # Convert to absolute path based on the root project directory
    if not os.path.isabs(credentials_path):
        root_dir = os.path.dirname(os.path.dirname(__file__))  # this goes up from /backend
        credentials_path = os.path.join(root_dir, credentials_path)

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credential file not found at: {credentials_path}")

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

# -----------------------------------------------------------------------------
# OCR helper
# -----------------------------------------------------------------------------

def extract_text_from_image(image_path: str) -> str:
    """Send an image to Google Vision OCR and return raw text."""
    _load_google_credentials()
    client = vision.ImageAnnotatorClient()
    with open(image_path, "rb") as fh:
        image = vision.Image(content=fh.read())

    response = client.text_detection(image=image)
    if response.error.message:
        raise RuntimeError(f"Google OCR error: {response.error.message}")

    return response.text_annotations[0].description if response.text_annotations else ""

# -----------------------------------------------------------------------------
# Robust receipt / invoice text parser
# -----------------------------------------------------------------------------

PRICE_RE    = r"-?\d+\.\d{2}"
ONLY_PRICE  = re.compile(fr"^\$?({PRICE_RE})$")
NAME_PRICE  = re.compile(fr"^(?P<name>.+?)\s+\$?(?P<price>{PRICE_RE})\s*$")

TAX_KEYWORDS   = {"tax", "sales tax", "vat"}
FEE_KEYWORDS   = {"fee", "service charge", "gratuity", "service fee", "tip"}
SUB_KEYWORDS   = {"subtotal"}
TOTAL_KEYWORDS = {
    "total due", "total", "amount due", "balance", "net total",
    "credit", "refund", "total refund",
}


def _classify(name: str) -> str:
    n = name.lower()
    if any(k in n for k in TAX_KEYWORDS):
        return "tax"
    if any(k in n for k in FEE_KEYWORDS):
        return "fee"
    if any(k in n for k in SUB_KEYWORDS):
        return "subtotal"
    if any(k in n for k in TOTAL_KEYWORDS):
        return "total"
    return "item"


def parse_receipt_text(text: str) -> Dict:
    """Parse OCR text. Works even if OCR splits the price onto its own line."""
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    items: List[Dict[str, float]] = []
    tax = fee = 0.0
    subtotal = None
    total = None

    pending_name: str | None = None  # hold name when price appears on next line

    for line in raw_lines:
        # Case A: line has both name and price ---------------------------------
        if m := NAME_PRICE.match(line):
            name  = m.group("name").strip(" .:-")
            price = float(m.group("price"))
            kind  = _classify(name)
        # Case B: line is *only* a price – use previously buffered name --------
        elif ONLY_PRICE.match(line) and pending_name:
            name  = pending_name
            price = float(line.strip("$"))
            kind  = _classify(name)
            pending_name = None
        # Case C: line has no trailing price – could be name waiting for price -
        else:
            pending_name = line  # store, continue to next
            continue

        # Dispatch based on kind ----------------------------------------------
        if kind == "tax":
            tax += price
        elif kind == "fee":
            fee += price
        elif kind == "subtotal":
            subtotal = price
        elif kind == "total":
            total = price
        else:
            items.append({"name": name, "price": price})

    # Fallback when OCR split removed the pair entirely ------------------------
    if not items:
        base = subtotal if subtotal is not None else (total if total is not None else 0.0)
        items.append({"name": "Subtotal", "price": base})

    if total is None:
        total = round(sum(i["price"] for i in items) + tax + fee, 2)

    return {"items": items, "tax": tax, "fee": fee, "total": total}
