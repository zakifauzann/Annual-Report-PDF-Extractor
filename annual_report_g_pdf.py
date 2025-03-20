import os
import json
import sys
import re  # Import the regular expression module
from pypdf import PdfReader
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pathlib import Path

# Load environment variables
load_dotenv(os.path.join(os.path.expanduser("~") , ".passkey" , ".env"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Using GOOGLE_API_KEY

if not GOOGLE_API_KEY:
    print("Error: Missing GOOGLE_API_KEY in .env file")
    sys.exit(1)

# Configure Gemini API
try:
    client = genai.Client(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    sys.exit(1)


def analyze_text_with_gemini(pdf_path):
    """Send extracted text to Gemini AI and get structured JSON data, with improved error handling."""
    prompt = f"""
    You are an expert in financial analysis and annual reports with accuracy and no mistakes. Your ABSOLUTE TOP PRIORITY is to extract specific information from the provided text and output the response in a STRICTLY VALID JSON format. If information is not found, leave the corresponding field empty or null.

    EXTRACT THE FOLLOWING INFORMATION:

    1.  **Executive Directors**: (title, name, total remuneration (salary, bonuses, others if available), and age). If age is not explicitly stated, do not attempt to calculate or estimate it. For salary, if there are two sources, for example, remuneration from the company and the group, sum both in the respected place. Exclude resigned director, only extract from current executive directors.
    
    2. For 2a and 2b below, go to the table of content of the annual report, find the "FINANCIAL STATEMENTS" section, then go to the "Notes To The Financial Statements" subsection and only search for the answers in those pages.
    
    2a.  **Geographical Segments/Geographical Information**: (name, total revenue and percentage).
        *   Only take values from the "Geographical Segments" or "Geographical Information".
        *   **DO NOT USE** any values from REVIEW OF PERFORMANCE or REVIEW OF FINANCIAL PERFORMANCE section.
        *   Ignore if stated with "-".
        *   **All revenue figures are in RM'000 (Ringgit Malaysia thousands).** When extracting numerical values, ensure that you are reporting the values in thousands of Ringgit Malaysia. If a number appears without the "RM'000" indicator, assume that it is already in thousands of Ringgit Malaysia.

    2b.  **Business Segments**: (name, total revenue and percentage).
        *   You MUST find a section titled "Business Segments" or "Business Information".
        *   **DO NOT USE** any values from "REVIEW OF PERFORMANCE" or "REVIEW OF FINANCIAL PERFORMANCE".
        *   These accurate revenue numbers are in tables. Avoid revenue found in paragraph or in long text.
        *   The **first priority** for revenue extraction is **"External Operating Revenue".**  
        *   If "External Operating Revenue" is **not found**, extract **"Total Operating Revenue"** as a fallback.
        *   Read "-" as 0 (zero). If a business segment has a revenue of zero, represent the revenue as 0 and the percentage as 0.0.
        *   **All revenue figures are in RM'000 (Ringgit Malaysia thousands).** When extracting numerical values, ensure that you are reporting the values in thousands of Ringgit Malaysia. If a number appears without the "RM'000" indicator, assume that it is already in thousands of Ringgit Malaysia.

    3.  **Major Customers**: (name, total revenue and percentage). Only take values from latest year. Read "-" as 0. If it has a revenue of zero, represent the revenue as 0 and the percentage as 0.0.

    4.  **Corporate Structure**:
            -   **Subsidiaries (own >= 50%)**: Extract name, principal activities, and ownership percentage from 1 to 100.
            -   **Associates (own < 50%)**: Extract name, principal activities, and ownership percentage from 1 to 100.
            -   **Subsidiaries/Associates (Unknown ownership)**: Extract name and principal activities.

    5.  **Land Areas**: (in square feet).

    6.  **Top 30 Shareholders**:
            -   **Date of shareholdings update**
            -   **Total number of shares**
            -   **Treasury shares (if applicable)**
            -   List all shareholders and state their percentage. If more than 30 shareholders are listed, only include the top 30.
            -   Distinguish between the nominee entities and the individuals or entities they represent. For each entry, list:
                *   The nominee (if applicable, e.g., "BI Nominees (Tempatan) Sdn Bhd").
                *   The represented shareholder (if applicable, e.g., "Rajesh A/L Jaikishan" in "Kenanga Nominees (Tempatan) Sdn Bhd for Rajesh A/L Jaikishan").
                *   The number of shares.
                *   If the shareholder is an individual or entity without a nominee, indicate that there is no nominee. Provide the total shares and percentage at the end.
            -   Represent the percentage as numbers from 1 to 100, ie : 2.27% -> 2.27

    OUTPUT REQUIREMENTS (MUST BE FOLLOWED EXACTLY):

    *   THE OUTPUT MUST BE A VALID JSON OBJECT.  THIS IS YOUR TOP PRIORITY.
    *   Use clear and descriptive keys for each extracted field.
    *   IF A SPECIFIC PIECE OF INFORMATION IS NOT FOUND IN THE TEXT, SET THE CORRESPONDING VALUE TO `null`. DO NOT MAKE UP INFORMATION.
    *   Ensure that numerical values are represented as NUMBERS (e.g., 1234567.89), NOT STRINGS ("1234567.89"). Percentages should be decimals (e.g., 0.25 for 25%).
    *   Arrays should be used to represent lists of items (e.g., a list of Executive Directors).
    *   Include ALL the fields from the example, even if the value is `null`.
    """

    try:
        # Generate content using Gemini AI
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                temperature=0.3  # Low temperature for consistent outputs, low randomness
            ),
            contents=[
                types.Part.from_bytes(
                    data=Path(pdf_path).read_bytes(),
                    mime_type='application/pdf',
                ),
                prompt
            ]  
        )

        print(response.usage_metadata)
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
    pdf_path = os.path.join('klk-annual_abridged.pdf')  # Replace with the actual path to your PDF file

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found.")
        sys.exit(1)

    print(f"Processing PDF: {pdf_path}")


    structured_data = analyze_text_with_gemini(pdf_path)

    # Change output file name to match the PDF file name
    pdf_file_name = os.path.splitext(os.path.basename(pdf_path))[0]  # Get PDF file name without extension
    output_file = f"{pdf_file_name}_extracted.json"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)  # Ensure UTF-8 encoding
        print(f"Extraction complete! Data saved to {output_file}")
    except Exception as e:
        print(f"ERROR: Error writing to file: {e}")