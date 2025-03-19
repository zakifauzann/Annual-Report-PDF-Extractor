import os
import json
import sys
import re  # Import the regular expression module
from pypdf import PdfReader
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Using GOOGLE_API_KEY

if not GOOGLE_API_KEY:
    print("Error: Missing GOOGLE_API_KEY in .env file")
    sys.exit(1)

# Configure Gemini API
try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    sys.exit(1)


def extract_text_from_pdf(pdf_path):
    """Extract text from a given PDF file, handling potential errors."""
    try:
        reader = PdfReader(pdf_path)
        extracted_text = ""
        for page in reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:  # Check if text was extracted successfully
                    extracted_text += page_text + "\n"
            except Exception as e:
                print(f"Error extracting text from page")  # Simplified error message
        return extracted_text
    except FileNotFoundError:
        print(f"Error: PDF file not found at path: {pdf_path}")
        return ""
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""


def analyze_text_with_gemini(text):
    """Send extracted text to Gemini AI and get structured JSON data, with improved error handling."""
    prompt = f"""
    You are an expert in financial analysis and annual reports. Your ABSOLUTE TOP PRIORITY is to extract specific information from the provided text and output the response in a STRICTLY VALID JSON format. If information is not found, leave the corresponding field empty or null.

    EXTRACT THE FOLLOWING INFORMATION:

    1.  **Executive Directors**: (title, name, total remuneration (salary, bonuses, others if available), and age). If age is not explicitly stated, do not attempt to calculate or estimate it. For salary, if there are two sources, for example, remuneration from the company and the group, sum both in the respected place. 

    2.  **Geographical Segments/Geographical Information**: (name, total revenue and percentage). Only take values from geographical segment or geographical information. Ignore if stated with "-". Prioritize the information found in financial statements related section in the report or operating segments in the report.

    3.  **Business Segments**: (name, total revenue and percentage). Read "-" as 0. Prioritize the information found in financial statements related section in the report or operating segments in the report.

    4.  **Major Customers**: (total revenue and percentage).

    5.  **Corporate Structure**:
        -   **Subsidiaries (own >= 50%)**: Extract name, principal activities, and ownership percentage from 1 to 100.
        -   **Associates (own < 50%)**: Extract name, principal activities, and ownership percentage from 1 to 100.
        -   **Subsidiaries/Associates (Unknown ownership)**: Extract name and principal activities.

    6.  **Land Areas**: (in square feet).

    7.  **Top 30 Shareholders**:
        -   **Date of shareholdings update**
        -   **Total number of shares**
        -   **Treasury shares (if applicable)**
        -   List all shareholders and state their percentage. If more than 30 shareholders are listed, only include the top 30.

    OUTPUT REQUIREMENTS (MUST BE FOLLOWED EXACTLY):

    *   THE OUTPUT MUST BE A VALID JSON OBJECT.  THIS IS YOUR TOP PRIORITY.
    *   Use clear and descriptive keys for each extracted field.
    *   IF A SPECIFIC PIECE OF INFORMATION IS NOT FOUND IN THE TEXT, SET THE CORRESPONDING VALUE TO `null`. DO NOT MAKE UP INFORMATION.
    *   Ensure that numerical values are represented as NUMBERS (e.g., 1234567.89), NOT STRINGS ("1234567.89"). Percentages should be decimals (e.g., 0.25 for 25%).
    *   Arrays should be used to represent lists of items (e.g., a list of Executive Directors).
    *   Include ALL the fields from the example, even if the value is `null`.
    """

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt + "\n\n" + text)

        # Extract JSON using regex to handle extra text
        match = re.search(r"\{.*}", response.text, re.DOTALL)
        if match:
            json_text = match.group(0)
        else:
            print("ERROR: Could not extract JSON from Gemini response.")
            json_text = "{}"

        # Parse JSON
        try:
            json_data = json.loads(json_text)
            return json_data

        except json.JSONDecodeError as e:
            print(f"ERROR: JSON decoding error: {e}")
            return {}

    except Exception as e:
        print(f"ERROR: Gemini processing failed: {e}")
        return {}


if __name__ == "__main__":
    # Specify the PDF path here:
    pdf_path = "kgb-annual_abridged.pdf"  # Replace with the actual path to your PDF file

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found.")
        sys.exit(1)

    print(f"Processing PDF: {pdf_path}")

    extracted_text = extract_text_from_pdf(pdf_path)
    if not extracted_text:
        print("Error: No text extracted from PDF.")
        sys.exit(1)

    structured_data = analyze_text_with_gemini(extracted_text)

    # Change output file name to match the PDF file name
    pdf_file_name = os.path.splitext(os.path.basename(pdf_path))[0]  # Get PDF file name without extension
    output_file = f"{pdf_file_name}.json"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)  # Ensure UTF-8 encoding
        print(f"Extraction complete! Data saved to {output_file}")
    except Exception as e:
        print(f"ERROR: Error writing to file: {e}")