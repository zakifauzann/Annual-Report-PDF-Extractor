import json
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)


def extract_info_from_text(text):
    prompt = f"""
    Extract the following information from the provided text:

    1. Executive Directors (title, name, total remuneration (salary, bonuses, others if available), and age).
    2. Geographical segments (total revenue and percentage).
    3. Business segments (total revenue and percentage).
    4. Major customers (total revenue and percentage).
    5. Corporate structure:
       - Subsidiaries (own >= 50%)
       - Associates (own < 50%)
       - Subsidiaries/Associates (Don't know)
       - Extract name, principal activities, and ownership percentage.
    6. Land areas (in square feet).
    7. Top 30 shareholders:
       - Date of shareholdings update
       - Total number of shares
       - Treasury shares (if applicable)
       - List all shareholders and state their percentage.

    Return the information in valid JSON format.

    Text:
    {text}
    """

    response = genai.chat(prompt)
    return response.text


if __name__ == "__main__":
    # Load extracted text from a file (replace with actual input method)
    with open("extracted_text.txt", "r", encoding="utf-8") as f:
        extracted_text = f.read()

    extracted_data = extract_info_from_text(extracted_text)

    # Save to JSON file
    with open("extracted_data.json", "w", encoding="utf-8") as json_file:
        json.dump(json.loads(extracted_data), json_file, indent=4)

    print("Extraction complete. Data saved to extracted_data.json")
