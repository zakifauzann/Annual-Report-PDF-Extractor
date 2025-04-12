import os
import json
import sys
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
import httpx

# Load environment variables
load_dotenv(os.path.join(os.path.expanduser("~"), ".passkey", ".env"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("Error: Missing GOOGLE_API_KEY in .env file")
    sys.exit(1)

# Configure Gemini API
try:
    client = genai.Client(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    sys.exit(1)


def read_prompt(file_path="annuals.txt"):
    """Read prompt from file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"ERROR: Failed to read prompt file: {e}")
        sys.exit(1)


def analyze_text_with_gemini(url_path):
    """Send extracted text to Gemini AI and get structured JSON data, with improved error handling."""
    try:
        doc_data = httpx.get(url_path).content
        prompt = read_prompt()

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(temperature=0.3),
            contents=[
                types.Part.from_bytes(
                    data=doc_data,
                    mime_type='application/pdf',
                ),
                prompt
            ]
        )

        print(response.usage_metadata)

        match = re.search(r"\{.*}", response.text, re.DOTALL)
        if match:
            json_text = match.group(0)
        else:
            print("ERROR: Could not extract JSON from Gemini response.")
            json_text = "{}"

        try:
            json_data = json.loads(json_text)
            return json_data

        except json.JSONDecodeError as e:
            print(f"ERROR: JSON decoding error: {e}")
            return {}

    except Exception as e:
        print(f"ERROR: Gemini processing failed: {e}")
        return {}


def from_db_link(url_path):
    print(f"Processing PDF: {url_path}")
    structured_data = analyze_text_with_gemini(url_path)

    pdf_file_name = os.path.splitext(os.path.basename(url_path))[0]
    output_file = f"{pdf_file_name}_extracted.json"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)
        print(f"Extraction complete! Data saved to {output_file}")
    except Exception as e:
        print(f"ERROR: Error writing to file: {e}")


if __name__ == "__main__":
    url_path = "https://anns.sgp1.cdn.digitaloceanspaces.com/3443412.pdf"
    from_db_link(url_path)
