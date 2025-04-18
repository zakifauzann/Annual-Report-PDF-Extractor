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
    prompt = """
   You are an expert in financial analysis and annual reports. Your ABSOLUTE TOP PRIORITY is to extract specific information from the provided text and output the response in a STRICTLY VALID JSON format. If information is not found, leave the corresponding field empty or null.

EXTRACT THE FOLLOWING INFORMATION:

1. **Executive Directors**: (title, name, age, and total remuneration (salary, bonuses, other compensation, if available)).
    *   If age is not explicitly stated, do not include it.
    *   For salary, if there are multiple sources of remuneration (e.g., from the company and a group entity), sum all applicable amounts and report the total remuneration. Specify the currency.
    *   If total remuneration is not available or cannot be reliably calculated, set the `total_remuneration` to `null`.

2. **Geographical Segments/Geographical Information**: (name, total revenue, and percentage of total revenue).
    *   Extract data ONLY from the "Geographical Segments" or "Geographical Information" section within the "Notes To The Financial Statements."
    *   Extract the revenue from external customers by geographical location from the annual report. This information is typically located in the notes to the financial statements, often under a section titled "Segment Reporting," "Operating Segments," or "Geographical Segments."
    *   The revenue should be broken down by geographical regions, and the values are expected to be in RM'000
    *   Revenue from external customers by geographical location of customers
    *   Extract directly from table rows if the data is presented in a table format.
    *   **CRITICAL:** If a table with geographical segments information is absent in the "Notes To The Financial Statements", set the entire "Geographical Segments" value to `null`. Do NOT use information from other sections of the report.
    *   Ignore rows or segments marked with "-". If a segment is ignored, do not include the corresponding key-value pair.

3. **Business Segments**: (name, total revenue, and percentage of total revenue).
    *   From the "Segment Information" table in the "Notes to the Financial Statements" section, extract the total revenue for each business segment. List each business segment along with its corresponding external revenue
    *   Get the total revenue per business segment as well
    *   The values are expected to be in RM'000 , note the currency used in the currency_unit
    *   **CRITICAL:** You MUST find a section titled "Business Segments," "Business Information," or "Segment Information" in the "Notes To The Financial Statements" section of the annual report.
    *   **AVOID**: Do NOT use numbers from *Review of Performance* or *Review of Financial Performance*.
    *   Treat "-" as 0 (zero). If a business segment has zero revenue, represent the revenue as `0` (a number) and the percentage as `0.0` (a number).

4.  **Major Customers**: (name, total revenue, year and percentage). "-" in the table means no revenue available for that year. Count as null. If the revenue for the current year is not available or not present in the table, also count as null.


5. **Corporate Structure**: (information from *INVESTMENT IN SUBSIDIARIES*, *SUBSIDIARIES, ASSOCIATES AND JOINT VENTURES*, *SUBSIDIARIES*, or related sections)
    *   **Subsidiaries (ownership >= 50%)**: Extract name, principal activities, and ownership percentage (as a number from 1 to 100).
    *   **Associates (ownership < 50%)**: Extract name, principal activities, and ownership percentage (as a number from 1 to 100).
    *   **Subsidiaries/Associates (Unknown ownership)**: Extract name and principal activities.

6. **Land Areas**: (in square feet - MUST be a number). If not found, set to `null`.

7. **Top 30 Shareholders**:
    *   **Date of shareholdings update**
    *   **Total number of shares** (total number of shares issued by the company)
    *   **Treasury shares (if applicable)**
    *   Distinguish between the nominee entities and the individuals or entities they represent. For each entry, list:
        *   The nominee (if applicable, e.g., "BI Nominees (Tempatan) Sdn Bhd").
        *   The represented shareholder (if applicable, e.g., "Rajesh A/L Jaikishan" in "Kenanga Nominees (Tempatan) Sdn Bhd for Rajesh A/L Jaikishan").
        *   The number of shares.
        *   If the shareholder is an individual or entity without a nominee, indicate that there is no nominee. Provide the total shares and percentage at the end.
    *   Represent the percentage as numbers from 1 to 100, ie : 2.27% -> 2.27
    *   Check the next page of the report as well for continuation of shareholder list

OUTPUT REQUIREMENTS (MUST BE FOLLOWED EXACTLY):

*   THE OUTPUT MUST BE A VALID JSON OBJECT.  THIS IS YOUR TOP PRIORITY.
*   Use clear and descriptive keys for each extracted field.
*   IF A SPECIFIC PIECE OF INFORMATION IS NOT FOUND IN THE TEXT, SET THE CORRESPONDING VALUE TO `null`. DO NOT MAKE UP INFORMATION.
*   Ensure that numerical values are represented as NUMBERS (e.g., 1234567.89), NOT STRINGS ("1234567.89"). Percentages should be numbers (e.g., 25.0 for 25%).
*   Arrays should be used to represent lists of items (e.g., a list of Executive Directors).
*   Include ALL the fields/keys from the example structure (provided below, or in previous turns), even if the value is `null`. This maintains a consistent JSON structure.
        {
        "executive_directors": [
            {
            "title": "Chief Executive Officer",
            "name": "Alice Johnson",
            "age": 55,
            "remuneration": {
                "salary": 1200000,
                "directorFees": 30000,
                "meetingAllowance": 2500,
                "otherEmoluments": 230623
                },
            "total remuneration" : 1463123
            "remuneration_currency_unit":"RM"
            },
    
        ],
        "geographical_segments": [
            {
            "segment": "Malaysia",
            "total_revenue": 500000000.00,
            "percentage": 0.60
            },
            {
            "segment": "Thailand",
            "total_revenue": 250000000.00,
            "percentage": 0.30
            },
            {
            "segment": "China",
            "total_revenue": 83333333.33,
            "percentage": 0.10
            }
        ],
        "business_segments": [
            {
            "segment": "Software",
            "total_revenue" : 4500000.00
            "currency_unit" : "RM'000",
            "percentage": 0.48
            },
            {
            "segment": "Manufacturing",
            "total_revenue": 350000000.00,
            "currency_unit" : "RM'000",
            "percentage": 0.42
            },
            {
            "segment": "Services",
            "total_revenue": 2234500.00,
            "currency_unit" : "RM'000",
            "percentage": 0.10
            }
        ],
        "major_customers": [
            {
            "customer name": "Customer 2",
            "segment" : "construction"
            "total_revenue": 0,
            "currency_unit" : "RM'000"
            "percentage": 0,
            },
            {
            "customer name": "Customer C",
            "segment" : "construction"
            "total_revenue": 75000000.00,
            "currency_unit" : "RM'000"
            "percentage": 0.09,
            }
        ],
        "corporate_structure": {
            "subsidiaries": [
            {
                "name": "Alpha Ltd",
                "principal_activities": "Software Development",
                "ownership_percentage": 0.80
            },
            {
                "name": "Gamma Corp",
                "principal_activities": "Hardware Manufacturing",
                "ownership_percentage": 1.00
            }
            ],
            "associates": [
            {
                "name": "Delta Inc",
                "principal_activities": "Research and Development",
                "ownership_percentage": 0.30
            }
            ],
            "unknown_ownership": [
            {
                "name": "Epsilon Group",
                "principal_activities": "Marketing and Sales"
            }
            ]
        },
        "land_areas": [
            {"land" : Tanah ABC
            "area"  :1230
            "unit"  : "hectares"/"sq ft"}
        ],
        "top_30_shareholders": {
            "shareholdings_update_date": "DAY-MONTH-YEAR",
            "total_shares": 10000000.00,
            "treasury_shares": 500000.00,
            "shareholders": [
            {
                "nominee/trustee": BI Nominees (Tempatan) Sdn Bhd
                "represented shareholder": Rajesh A/L Jaikishan
                "shares": 45,730,000
                "percentage": 6.20%
            },
            ]
        }
    }
    """

    try:
        # Generate content using Gemini AI
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                temperature=0.5  # Low temperature for consistent outputs, low randomness
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


def calculate_percentage(structured_data):

    # Calculate percentage for segments
    geographical_segments = structured_data.get('geographical_segments', []) 
    if geographical_segments:
        total_revenue = sum(segment['total_revenue'] for segment in geographical_segments if segment.get('total_revenue') is not None)
        for segment in geographical_segments:
            if segment.get('total_revenue') is not None:
                segment['percentage'] = (segment['total_revenue'] / total_revenue * 100) if total_revenue > 0 else 0
            else:
                segment['percentage'] = 0  # Handle NoneType

    # Calculate percentage for business segments
    business_segments = structured_data.get('business_segments', [])
    if business_segments:
        total_business_revenue = sum(business['total_revenue'] for business in business_segments if business.get('total_revenue') is not None)
        for business in business_segments:
            if business.get('total_revenue') is not None:
                business['percentage'] = (business['total_revenue'] / total_business_revenue * 100) if total_business_revenue > 0 else 0
            else:
                business['percentage'] = 0  # Handle NoneType

    # Calculate percentage for major customers
    major_customers = structured_data.get('major_customers', [])
    if major_customers:
        total_customer_revenue = sum(customer['total_revenue'] for customer in major_customers if customer.get('total_revenue') is not None)
        for customer in major_customers:
            if customer.get('total_revenue') is not None:
                customer['percentage'] = (customer['total_revenue'] / total_customer_revenue * 100) if total_customer_revenue > 0 else 0
            else:
                customer['percentage'] = 0  # Handle NoneType

    calc_data = structured_data
    return calc_data

def save_json(structured_data, pdf_path, calc_flag = False):
    # Change output file name to match the PDF file name
    pdf_file_name = os.path.splitext(os.path.basename(pdf_path))[0]  # Get PDF file name without extension
    if not calc_flag:
        output_file = os.path.join("json" , f"{pdf_file_name}_pdf.json")
    elif calc_flag:
        output_file = os.path.join("json" , f"{pdf_file_name}_calc.json")


    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)  # Ensure UTF-8 encoding
        print(f"Extraction complete! Data saved to {output_file}")
    except Exception as e:
        print(f"ERROR: Error writing to file: {e}")
    

if __name__ == "__main__":
    # Specify the PDF path here:
    pdf_path = os.path.join("pdf", "kgb-annual_abridged.pdf")  # Replace with the actual path to your PDF file

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found.")
        sys.exit(1)

    print(f"Processing PDF: {pdf_path}")

    # save data from AI
    structured_data = analyze_text_with_gemini(pdf_path)
    save_json(structured_data , pdf_path)

    # do calc then 
    pdf_file_name = os.path.splitext(os.path.basename(pdf_path))[0]  # Get PDF file name without extension
    with open(os.path.join("json", f"{pdf_file_name}_pdf.json"), "r", encoding='utf-8') as data:
        json_data = json.load(data)  # Load JSON data from the file

    calc_data = calculate_percentage(json_data)
    save_json(calc_data , pdf_path, calc_flag=True)

