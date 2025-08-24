# Purpose: This script converts a Tricare provider list PDF into a CSV file.
# Vibe coded by Shannon Zoch with assistance from Gemini.
#
# Version: 5.0
# Changes in this version:
# - Added the 'Medical Group' column back into the CSV output.
# - Implemented a fix to prevent 'Specialties:' from bleeding into the 'Languages Spoken' field.
# - Updated column order in the final CSV.

import re
import csv
import sys
import PyPDF2

def extract_text_from_pdf(pdf_path):
    """
    Extracts all text from a given PDF file.

    Args:
        pdf_path (str): The file path to the PDF.

    Returns:
        str: The concatenated text from all pages of the PDF.
    """
    print(f"Reading text from {pdf_path}...")
    full_text = ""
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                # Adding a space helps prevent words from merging across lines
                full_text += page.extract_text() + "\n"
        print("Successfully extracted text.")
        return full_text
    except FileNotFoundError:
        print(f"Error: The file '{pdf_path}' was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while reading the PDF: {e}")
        sys.exit(1)


def parse_provider_data(text):
    """
    Parses provider information from the extracted PDF text. This version first
    splits the text into blocks for each provider and then parses each block.

    Args:
        text (str): The raw text extracted from the PDF.

    Returns:
        list: A list of dictionaries, where each dictionary contains the
              details of a single provider.
    """
    print("Parsing provider data...")
    providers = []

    # Split the text into blocks, where each block starts with a provider's name.
    # The regex uses a positive lookahead `(?=...)` to split the text *before* the
    # name pattern, keeping the name in the resulting block.
    provider_blocks = re.split(r'\n(?=[\w\s,.\'-]+, (?:MD|DO)\n)', text)

    for block in provider_blocks:
        # Skip any blocks that don't look like a valid provider entry.
        if "Phone:" not in block or "Gender:" not in block:
            continue

        try:
            # --- Field Extraction using targeted regex ---

            name_match = re.search(r"([\w\s,.'-]+, (?:MD|DO))", block)
            phone_match = re.search(r"Phone:\s*(\(\d{3}\)\s*\d{3}-\d{4})", block)
            gender_match = re.search(r"Gender:\s*(Male|Female)", block)
            languages_match = re.search(r"Languages Spoken:\s*([^\n]+)", block)
            specialties_block_match = re.search(r"Specialties:\s*([\s\S]*?)(?:\n\s*\n|Group Affiliations:)", block, re.DOTALL)

            # --- Data Cleaning and Assignment ---

            name = ' '.join(name_match.group(1).replace(',', '').split()) if name_match else 'N/A'
            phone = phone_match.group(1).strip() if phone_match else 'N/A'
            gender = gender_match.group(1).strip() if gender_match else 'N/A'
            
            if languages_match:
                languages_text = languages_match.group(1).strip()
                # Fix for when "Specialties:" gets merged onto the same line
                if "Specialties:" in languages_text:
                    languages_text = languages_text.split("Specialties:")[0].strip()
                languages = languages_text.replace(', ', ' & ')
            else:
                languages = 'N/A'
            
            if specialties_block_match:
                specialties_raw = specialties_block_match.group(1).strip()
                specialties_text = ' '.join(line.strip() for line in specialties_raw.split('\n'))
                specialties = re.sub(r'\s*,\s*', ' - ', specialties_text).strip()
            else:
                specialties = 'N/A'

            # --- Logic for Service Type (Address) and Medical Group ---
            
            service_type = ''
            medical_group = ''
            header_block_match = re.search(r"(?:MD|DO)\s*\n([\s\S]*?)Phone:", block)
            
            if header_block_match:
                header_lines = [line.strip() for line in header_block_match.group(1).strip().split('\n') if line.strip()]
                
                if any("Telemedicine" in s for s in header_lines):
                    service_type = "Telemedicine"
                    try:
                        medical_group = next(line for line in header_lines if "telemedicine" not in line.lower())
                    except StopIteration:
                        medical_group = "N/A"
                else:
                    if header_lines:
                        medical_group = header_lines[0]
                        address_parts = header_lines[1:]
                        address_parts = [part for part in address_parts if not re.match(r'^\d+\.\d+ miles$', part)]
                        service_type = ' '.join(address_parts)

            providers.append({
                'Name': name,
                'Service Type': service_type,
                'Medical Group': medical_group,
                'Phone': phone,
                'Gender': gender,
                'Languages Spoken': languages,
                'Specialties': specialties,
            })
        except Exception as e:
            print(f"--- Skipping a block due to parsing error: {e} ---")
            print(f"{block[:250]}...")
            print("-------------------------------------------------")


    print(f"Found and parsed {len(providers)} providers.")
    return providers


def write_to_csv(providers_data, output_filename):
    """
    Writes the parsed provider data to a CSV file.

    Args:
        providers_data (list): A list of provider dictionaries.
        output_filename (str): The name of the output CSV file.
    """
    if not providers_data:
        print("No provider data to write.")
        return

    print(f"Writing data to {output_filename}...")
    # Explicitly define the fieldnames to ensure correct column order.
    fieldnames = ['Name', 'Service Type', 'Medical Group', 'Phone', 'Gender', 'Languages Spoken', 'Specialties']
    try:
        with open(output_filename, 'w', newline='', encoding='utf-8') as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(providers_data)
        print("CSV file created successfully.")
    except IOError as e:
        print(f"Error writing to file {output_filename}: {e}")
        sys.exit(1)


def main():
    """
    Main function to execute the PDF to CSV conversion process.
    """
    if len(sys.argv) != 3:
        print("Usage: python ProviderPDFtoCSV.py <input_pdf_path> <output_csv_path>")
        sys.exit(1)

    pdf_file_path = sys.argv[1]
    csv_output_path = sys.argv[2]
    
    # Step 1: Extract text from the PDF
    raw_text = extract_text_from_pdf(pdf_file_path)

    # Step 2: Parse the extracted text to get provider data
    providers = parse_provider_data(raw_text)

    # Step 3: Write the parsed data to a CSV file
    write_to_csv(providers, csv_output_path)


if __name__ == "__main__":
    main()
