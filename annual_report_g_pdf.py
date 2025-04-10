import os
import json
import sys
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pathlib import Path
import httpx

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


def analyze_text_with_gemini(url_path):
    """Send extracted text to Gemini AI and get structured JSON data, with improved error handling."""
    prompt = f"""
    You are an expert in financial analysis and annual reports with accuracy and no mistakes. Your ABSOLUTE TOP PRIORITY is to extract specific information from the provided text and output the response in a STRICTLY VALID JSON format. If information is not found, leave the corresponding field empty or null.

    EXTRACT THE FOLLOWING INFORMATION:

    1.  Extract details for the following executive positions: Chief Executive Officer (CEO), Group Managing Director, Chief Operating Officer (COO), and Executive Directors. Include:
        *   Title
        *   Name
        *   Total remuneration (sum of salary, bonuses, and other components if available)
        *   Age (only if explicitly stated; do not estimate)
        *   Exclusions:
        *   Do not include resigned directors—extract only current executives.
        *   Do not include non-executive directors.
    
    2.  **Segmental Information** (Follow the instructions below):
        *   ONLY take revenue values from the "Segments Information" or "Segmental Information" subsection. DO NOT take from everywhere else.
        *   ONLY take revenue values from **"Total Operating Revenue"** or **"Total Revenue"**. DO NOT take values from **External Revenue** or **External Customers**.
        *   Calculate the percentage if the revenue has value.
        *   If revenues are found first before segmental information, just discard them and use revenues under Segmental Information subsection.
        *   **All revenue figures are in RM'000 (Ringgit Malaysia thousands).** When extracting numerical values, ensure that you are reporting the values in thousands of Ringgit Malaysia. If a number appears without the "RM'000" indicator, assume that it is already in thousands of Ringgit Malaysia.
    
        2a. **Geographical Segments/Geographical Information**: (name, total revenue and percentage).
            *   Ignore if stated with "-".
            
        2b. **Business Segments/Business Information**: (name, total revenue and percentage).
            *   Read "-" as 0 (zero).
        
    3.  **Major Customers**: (name, total revenue, year and percentage). "-" in the table means no revenue available for that year. Count as null. If the revenue for the current year is not available or not present in the table, also count as null. Calculate the percentage if the revenue has value.

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
    7. Company Name
    
    OUTPUT REQUIREMENTS (MUST BE FOLLOWED EXACTLY):

    *   THE OUTPUT MUST BE A VALID JSON OBJECT.  THIS IS YOUR TOP PRIORITY.
    *   Use clear and descriptive keys for each extracted field.
    *   IF A SPECIFIC PIECE OF INFORMATION IS NOT FOUND IN THE TEXT, SET THE CORRESPONDING VALUE TO `null`. DO NOT MAKE UP INFORMATION.
    *   Ensure that numerical values are represented as NUMBERS (e.g., 1234567.89), NOT STRINGS ("1234567.89"). Percentages should be decimals (e.g., 0.25 for 25%).
    *   Arrays should be used to represent lists of items (e.g., a list of Executive Directors).
    *   Include ALL the fields from the example, even if the value is `null`.
    """

    try:
        doc_url = url_path  # Replace with the actual URL of your PDF
        doc_data = httpx.get(doc_url).content
        # Generate content using Gemini AI
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                temperature=0.3  # Low temperature for consistent outputs, low randomness
            ),
            contents=[
                types.Part.from_bytes(
                    data=doc_data,
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
    url_path = "https://anns.sgp1.cdn.digitaloceanspaces.com/3538766.pdf" # Replace with the actual path to your PDF file

    print(f"Processing PDF: {url_path}")


    structured_data = analyze_text_with_gemini(url_path)

    # Change output file name to match the PDF file name
    pdf_file_name = os.path.splitext(os.path.basename(url_path))[0]  # Get PDF file name without extension
    output_file = f"{pdf_file_name}_extracted.json"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)  # Ensure UTF-8 encoding
        print(f"Extraction complete! Data saved to {output_file}")
    except Exception as e:
        print(f"ERROR: Error writing to file: {e}")