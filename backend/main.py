import os
from dotenv import load_dotenv
import tempfile
import uuid
from typing import List
from fastapi import FastAPI, UploadFile, Form
from ocr_parser import extract_text_from_image, parse_receipt_text
from chatbot_splitter import get_split_suggestion

load_dotenv() 
app = FastAPI()

@app.post("/analyze/")
async def analyze_receipt(
    file: UploadFile,
    instruction: str = Form(...),
    names: str = Form(...),
):
    # save upload to a temp file (Vision API needs a path)
    ext      = os.path.splitext(file.filename or "receipt.jpg")[1]
    tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}{ext}")
    with open(tmp_path, "wb") as fh:
        fh.write(await file.read())

    # OCR + parse
    ocr_text = extract_text_from_image(tmp_path)
    parsed   = parse_receipt_text(ocr_text)
    os.remove(tmp_path)

    # split suggestion
    name_list: List[str] = [n.strip() for n in names.split(",") if n.strip()]
    suggestion           = get_split_suggestion(parsed, instruction, name_list)

    return {"parsed": parsed, "suggestion": suggestion}
