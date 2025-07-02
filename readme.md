
## Features

Scan or upload a photo of your receipt  
Automatically extract items and prices using OCR (Google Vision)  
Use natural language to explain how to split (e.g., "Alice had sushi, Bob had steak, George didn't touch the appetizers.")  
See how much each person owes - calculated for you!  
Clean web interface with Streamlit

---

## How It Works

| Component     | Description |
|--------------|-------------|
| **OCR (Google Cloud Vision)** | Reads receipt text from uploaded images |
| **Parsing** | Extracts items and prices using regex |
| **LLM Chatbot** | Understands your instructions and splits the bill |
| **FastAPI** | Backend logic and endpoints |
| **Streamlit** | Web interface for uploading, chatting, and viewing results |

---

## Preview

 

---

## Installation

```bash
# Clone the project
git clone https://github.com/cvhuynh1777/splitmate.git
cd receipt-splitter-app

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
