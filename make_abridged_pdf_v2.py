import fitz  # pymupdf is imported as fitz
import os

possible_keywords = ["management" , "executive", "director" ,"senior management", "corporate structure", "corporate", "corporate profile"
                    "chairman statement", "chairman", "discussion and analysis", "discussion", "analysis",
                    "financial statements" , "notes to financial statements", "notes to the financial statements",
                    "corporate info" , "vision and mission", "vision" , "mission" , 
                    "analysis of shareholdings" , "shareholders" , "shareholding" , "share", "account" , 
                    "salary" , "remuneration"]

statement_keywords = ["financial statements" , "notes to financial statements", "notes to the financial statements"]
finance_keywords = ["segment" , "geographical" , "business", "salary" , "remuneration" , "subsidiary" ,"subsidiaries", "associate" , "associates"]

exclude_keywords = ["sustainability report", "sustainability", "risk management", "share buy back" , "audit committee", "compliance"
                    "governance" , "internal control" , "general meeting" , "General Meetings" , "buy-back"]

def extract_titles_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)  # Open the PDF using fitz
        num_pages = len(doc)
        titles = []

        for page_num in range(num_pages):
            page = doc[page_num]

            # Heuristic: Take the first few lines as the potential title, excluding the header
            rect = page.rect  # Get the page rectangle
            header_height = 45  # Define the height of the header to be removed
            cropped_rect = fitz.Rect(rect.x0, rect.y0 + header_height, rect.x1, rect.y1)  # Define the crop box
            text = page.get_text("text", clip=cropped_rect)  # Extract text using the crop box
            lines = text.splitlines()  # Split the text into lines

            potential_title = ""
            # Heuristic: Take the first few lines as the potential title
            num_title_lines = min(4, len(lines))  # Consider up to 6 lines

            for i in range(num_title_lines):
                line = lines[i].strip()  # Remove leading/trailing whitespace

                if len(line) > 5 and len(line) < 100 : # Basic length checks
                    potential_title += line + " "

            potential_title = potential_title.strip() #Remove extra space
            titles.append(potential_title)

        doc.close()
        return titles

    except FileNotFoundError:
        print(f"Error: File not found at {pdf_path}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []
    
    
def check_segments(page_num, pdf_file_path):
    doc = fitz.open(pdf_file_path)
    page = doc[page_num]

    # Heuristic: Take the first few lines as the potential title, excluding the header
    rect = page.rect  # Get the page rectangle
    header_height = 45  # Define the height of the header to be removed
    cropped_rect = fitz.Rect(rect.x0, rect.y0 + header_height, rect.x1, rect.y1)  # Define the crop box
    text = page.get_text("text", clip=cropped_rect)  # Extract text using the crop box
    lines = text.splitlines()  # Split the text into lines

    for line in lines:
        if any(keyword in line.lower() for keyword in finance_keywords):
            return True
    else: return False


#from page titles, split into sections
def split_into_sections(page_titles , pdf_file_path):
    list_of_pages = []
    next_page_flag = False ## next_page flag
    count = 0
    if page_titles:
        page_num = 0
        for page_num, title in enumerate(page_titles):
            # print("Page:" , page_num , " -   ", title)  # debug
            if any(keyword in title.lower() for keyword in possible_keywords) and not any(keyword in title.lower() for keyword in exclude_keywords):
                if any(keyword in title.lower() for keyword in statement_keywords):
                    if check_segments(page_num , pdf_file_path) == False:
                        print("No Match SEGMENT:" , page_num , " -   ", title)  # debug
                        continue
                print("Match:" , page_num , " -   ", title)  # debug
                next_page_flag = True  ## possible next page is useful
                count = 0 ## reset next page counter
                list_of_pages.append(page_num)
                continue


            if title == "":
                if next_page_flag and count < 3:
                    print("Match:" , page_num , " -   ", title) # debug
                    list_of_pages.append(page_num)
                    count =  count + 1
                    continue
                else:
                    print("No Match : " , page_num , " - ", title) # debug
                    count = 0
                    next_page_flag = False
                    continue

            if any(keyword in title.lower() for keyword in exclude_keywords):
                print("No Match, IF : " , page_num , " - ", title) # debug
                next_page_flag = False
                continue

            else:
                print("No Match, ELSE : " , page_num , " - ", title) # debug

            
    return list_of_pages

def get_tableofcontents(filename):

    file  = fitz.open(filename)
    toc = file.get_toc()
    print("Table of Contents : ", toc)

# Example usage:
if __name__ == '__main__':
    pdf_file_path =  os.path.join("pdf", "rohas-annual.pdf")  # Replace with your PDF file path
    page_titles = extract_titles_from_pdf(pdf_file_path)
    page_numbers = split_into_sections(page_titles, pdf_file_path)
    get_tableofcontents(pdf_file_path)

   # make new pdf from the page numbers in sections
    with open(pdf_file_path, 'rb') as pdf_file:
        doc = fitz.open(pdf_file_path)  # Open the PDF using fitz
        new_pdf_name = pdf_file_path.split('.')[0] + '_abridged_v2.pdf'
        doc.select(page_numbers)
        doc.save(new_pdf_name)
        
    print(pdf_file_path)
    print("Length of abridged pdf: ", len(page_numbers))
