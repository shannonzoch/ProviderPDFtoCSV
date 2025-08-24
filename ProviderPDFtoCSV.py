# Purpose: This script converts a Tricare provider list PDF into a CSV file.
# Vibe coded by Shannon Zoch with assistance from Gemini.
#
# Version: 2.0
# Changes in this version:
# - Input and output filenames are now passed as command-line arguments.

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
    Parses provider information from the extracted PDF text using regex.

    Args:
        text (str): The raw text extracted from the PDF.

    Returns:
        list: A list of dictionaries, where each dictionary contains the
              details of a single provider.
    """
    print("Parsing provider data...")
    providers = []

    # Regex to capture a complete provider block. This pattern looks for key fields
    # like Name, Phone, Gender, Languages, and Specialties.
    # It handles both physical addresses and "Telemedicine".
    pattern = re.compile(
        r"(?P<name>[\w\s,]+, \w+, MD|[\w\s,]+, DO)\n"  # Name (e.g., Adkins, Amanda C, MD)
        r"\s*(?P<service_type>Telemedicine|[\s\S]*?Phone:)" # Service type (Telemedicine or address block)
        r"\s*(?P<group>[\w\s&'().-]+?)\n" # Medical Group
        r"\s*Phone:\s*(?P<phone>\(\d{3}\)\s*\d{3}-\d{4})" # Phone
        r"[\s\S]*?" # Ignore Fax, After Hours, etc.
        r"Gender:\s*(?P<gender>Male|Female)\n" # Gender
        r"\s*Languages Spoken:\s*(?P<languages>[\w\s,]+)\n" # Languages
        r"\s*Specialties:\s*(?P<specialties>[\s\S]*?)\n" # Specialties block
        r"\s*Group Affiliations:", # Stop capturing before Group Affiliations
        re.MULTILINE
    )

    for match in pattern.finditer(text):
        data = match.groupdict()

        # --- Data Cleaning ---

        # 1. Clean up the Name
        name = ' '.join(data['name'].replace(',', '').split())

        # 2. Clean up Service Type
        service_type = data['service_type'].strip()
        if service_type != 'Telemedicine':
            # If it's an address, clean it up by removing the trailing "Phone:"
            # and consolidating whitespace.
            address_text = service_type.rsplit('Phone:', 1)[0]
            service_type = ' '.join(address_text.split()).strip()
        
        # 3. Clean up Medical Group
        medical_group = ' '.join(data['group'].strip().split())
        # Sometimes the address bleeds into the group name, remove it.
        if "Phone:" in medical_group:
            medical_group = medical_group.split("Phone:")[0].strip()


        # 4. Clean up Specialties
        # The specialties can span multiple lines. We join them with " & ".
        specialties_raw = data['specialties'].strip()
        specialties_lines = [line.strip() for line in specialties_raw.split('\n')]
        specialties = ' & '.join(filter(None, specialties_lines))

        providers.append({
            'Name': name,
            'Service Type': service_type,
            'Medical Group': medical_group,
            'Phone': data['phone'].strip(),
            'Gender': data['gender'].strip(),
            'Languages': data['languages'].strip().replace(', ', ' & '),
            'Specialties': specialties,
        })

    print(f"Found {len(providers)} providers.")
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
    keys = providers_data[0].keys()
    try:
        with open(output_filename, 'w', newline='', encoding='utf-8') as output_file:
            writer = csv.DictWriter(output_file, fieldnames=keys)
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
