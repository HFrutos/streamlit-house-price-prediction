#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scrapes pisos.com for properties FOR RENT in a specified region (e.g., Madrid Capital).
This script performs a two-stage process in a single run:
1. Scrapes listing pages to get unique property URLs and their geolocation data.
2. For each unique URL found, scrapes the detailed information from the property's page.

All collected data (initial link info + detailed info) is then compiled and
saved into a single CSV file in the 'data/raw/' directory relative to the project root.
This script assumes it is located in a subdirectory of the project root (e.g., 'scrapers/').
"""

# Standard library imports
import json
import time
import re # For regular expression operations
from datetime import datetime
from pathlib import Path # For robust path manipulation

# Third-party library imports
import requests
from bs4 import BeautifulSoup
import pandas as pd

# --- Configuration Constants ---
PISOS_BASE_URL = "https://www.pisos.com"

# Initial page URL for properties for RENTAL in Madrid Capital.
# IMPORTANT: This URL should end with a trailing slash for correct pagination.
INITIAL_LISTING_URL_RENTAL = "https://www.pisos.com/alquiler/pisos-madrid_capital_zona_urbana/"

# Web scraping parameters
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
REQUEST_TIMEOUT_LISTING = 10  # Timeout for listing pages
REQUEST_TIMEOUT_DETAILS = 15  # Timeout for detail pages
POLITE_DELAY_SECONDS = 1.5    # Pause between requests

# JSON-LD script target property types
# These are common @type values for residential properties in JSON-LD schemas. Adjust if needed.
TARGET_PROPERTY_TYPES = ["SingleFamilyResidence", "Apartment", "Residence", "House", "Flat"]

# --- Output File Configuration for the final CSV ---
BASE_OUTPUT_CSV_FILENAME = "madrid_rental_properties_raw.csv"

# --- Determine Project and Data Directories ---
# Path to the directory containing this script.
SCRIPT_DIR = Path(__file__).resolve().parent

# *** IMPORTANT: Review and adjust PROJECT_ROOT definition if necessary ***
# The logic below attempts to find the project root based on common script locations.

# Option 1: Script is in a first-level subdirectory of the project (e.g., project_root/scrapers/).
# This is a common and recommended setup if you have a dedicated 'scrapers' folder.
PROJECT_ROOT = SCRIPT_DIR.parent
# Example: If SCRIPT_DIR is /path/to/streamlit-house-price-prediction/scrapers,
# then PROJECT_ROOT becomes /path/to/streamlit-house-price-prediction.

# Option 2: Script is located directly in the project root directory (e.g., project_root/your_script.py).
# Uncomment the line below AND comment out the 'PROJECT_ROOT = SCRIPT_DIR.parent' line above if this is the case.
# PROJECT_ROOT = SCRIPT_DIR
# Example: If SCRIPT_DIR is /path/to/streamlit-house-price-prediction,
# then PROJECT_ROOT also becomes /path/to/streamlit-house-price-prediction.

# For other script locations (e.g., nested more deeply within subdirectories,
# or if the script is outside the main project folder but needs to save data into it),
# the above automatic options might not correctly identify your project's true root.
# In such cases, you MUST manually set PROJECT_ROOT to the correct absolute path.
# For example:
# PROJECT_ROOT = Path("/absolute/path/to/your/streamlit-house-price-prediction")
# Ensure this path points to the top-level 'streamlit-house-price-prediction' directory.

# --- End of PROJECT_ROOT configuration ---

# Define the target directory for raw data
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
# Construct the full path for the output file
OUTPUT_CSV_FILEPATH = RAW_DATA_DIR / BASE_OUTPUT_CSV_FILENAME


# --- Helper Function for Text Cleaning ---
def clean_text(text):
    """
    Helper function to clean text by replacing multiple whitespace characters
    (including newlines, tabs) with a single space and stripping leading/trailing whitespace.

    Args:
        text (str or None): The input string to clean.

    Returns:
        str or None: The cleaned string, or None if the input was None.
    """
    if text:
        # Replace one or more whitespace characters with a single space
        text = re.sub(r'\s+', ' ', str(text)) 
        return text.strip()
    return None

# --- Functions for Link and Geolocation Scraping (from listing script) ---
def get_all_property_links_and_geo(base_url, initial_page_url):
    """
    Scrapes all listing pages from pisos.com starting from initial_page_url
    to get unique property links, latitudes, and longitudes.

    Args:
        base_url (str): The base domain (e.g., "https://www.pisos.com").
        initial_page_url (str): The URL of the first page of listings.
                                (Assumed to end with a trailing slash).

    Returns:
        list: A list of unique dictionaries, where each dictionary contains:
              'url' (str): The full URL to the property details page.
              'latitude' (str): The latitude of the property.
              'longitude' (str): The longitude of the property.
              'page_source' (int): The page number from which the info was first extracted.
    """
    all_properties_link_data = []
    seen_urls = set() # To keep track of processed URLs and avoid duplicates
    page_num = 1 # Start with page 1

    print(f"Stage 1: Starting link and geolocation data scraping from: {initial_page_url}")

    while True: # Loop indefinitely until a break condition (end of pages or error) is met
        if page_num == 1: # Construct URL for the current page
            current_url = initial_page_url
        else:
            # Assumes initial_page_url ends with a '/' for correct concatenation
            # Using rstrip to be sure, then adding one, for robust URL construction
            current_url = f"{initial_page_url.rstrip('/')}/{page_num}/"

        print(f"Scraping listing page {page_num}: {current_url}")
        
        response = None # Initialize response to handle potential errors before assignment
        try:
            # Fetch the HTML content of the page
            response = requests.get(
                current_url,
                headers={'User-Agent': USER_AGENT},
                timeout=REQUEST_TIMEOUT_LISTING
            )
            response.raise_for_status() # Raise an HTTPError for bad status codes (4xx or 5xx)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404 and page_num > 1:
                #  If a 404 error occurs on a subsequent page, assume it's the end of listings
                print(f"Page {page_num} ({current_url}) returned 404. Assuming end of listings.")
            else:
                # For other HTTP errors or 404 on the first page, log and stop
                print(f"HTTP error fetching listing page {current_url}: {e}")
            break # Stop scraping on HTTP errors
        except requests.exceptions.RequestException as e:
            # For other network-related errors (timeout, DNS failure, etc.)
            print(f"Request error fetching listing page {current_url}: {e}")
            break # Stop scraping on other request errors

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all JSON-LD script tags which usually contain structured data
        json_scripts = soup.find_all("script", type="application/ld+json")
        
        new_properties_found_on_this_page = 0

        # If no JSON-LD scripts are found on a subsequent page, it might indicate the end
        if not json_scripts and page_num > 1:
            print(f"No JSON-LD scripts found on listing page {page_num}. Assuming end of listings.")
            break

        # Process each found JSON-LD script tag
        for script_tag_content in json_scripts:
            try:
                if script_tag_content.string:
                    # Load the content of the script tag as JSON
                    data = json.loads(script_tag_content.string)
                else:
                    # Skip empty script tags
                    continue 

                # The JSON data can be a single dictionary or a list of dictionaries
                items_to_process = []
                if isinstance(data, list): 
                    items_to_process.extend(data)
                elif isinstance(data, dict): 
                    items_to_process.append(data)
                else:
                    # Skip if data is not a list or dict (unexpected format) 
                    continue

                # Iterate through items in the JSON-LD data
                for item in items_to_process:
                    # Check if the item is a dictionary and matches our target property types
                    # and contains the necessary 'geo' and 'url' fields.
                    if (isinstance(item, dict) and 
                            item.get("@type") in TARGET_PROPERTY_TYPES and 
                            "geo" in item and "url" in item):                        
                        prop_url_path = item.get("url")
                        
                        if prop_url_path:
                            # Construct the full URL. Handles relative and absolute paths.
                            full_url = base_url + prop_url_path if not prop_url_path.startswith(('http://', 'https://')) else prop_url_path
                            
                            # Skip if this URL has already been processed (duplicate)
                            if full_url in seen_urls:
                                continue 
                            
                            # Extract latitude and longitude
                            latitude = item.get("geo", {}).get("latitude")
                            longitude = item.get("geo", {}).get("longitude")
                            
                            if full_url and latitude and longitude:
                                # Store the extracted data
                                all_properties_link_data.append({
                                    "url": full_url,
                                    "latitude": str(latitude), # Ensure latitude is string for consistent JSON
                                    "longitude": str(longitude), # Ensure longitude is string
                                    "page_source": page_num # Page from listing where URL was found
                                })
                                seen_urls.add(full_url) # Mark URL as seen
                                new_properties_found_on_this_page += 1
            except json.JSONDecodeError:
                # Log and skip if a script tag contains invalid JSON.
                # De-comment the print below for debugging if needed.
                # print(f"Warning: Could not decode JSON from a script tag on {current_url}")
                continue
            except Exception as e:
                # Log other unexpected errors during script processing
                print(f"Unexpected error processing JSON-LD script tag on {current_url}: {e}")
                continue
        
        print(f"Found {new_properties_found_on_this_page} new unique property links on page {page_num}.")
        
        # Stopping condition: if no new properties are found on the current page
        if new_properties_found_on_this_page == 0:
            if page_num == 1:
                # If no properties found on the very first page, something is likely wrong
                print(f"No property links found on the first listing page: {initial_page_url}. Check URL or website structure. Stopping.")
            else:
                # If no new properties on a subsequent page, assume end of listings
                print(f"No new unique property links found on page {page_num}. Assuming end of listings.")
            break 
        
        # Increment page number for the next iteration
        page_num += 1
        # Polite delay to avoid overwhelming the server
        time.sleep(POLITE_DELAY_SECONDS)
    
    print(f"Stage 1: Finished. Found {len(all_properties_link_data)} unique property links.")
    
    return all_properties_link_data

# --- Helper Functions for Detail Extraction ---
def extract_price(soup):
    """
    Extracts the property price from the BeautifulSoup object of a property detail page.
    It tries multiple selectors in a prioritized order.

    Args:
        soup (BeautifulSoup): The parsed HTML content of the property page.

    Returns:
        int or None: The extracted price as an integer, or None if not found or unparseable.
    """
    details_div = soup.find("div", class_="details", attrs={"data-ad-price": True})
    if details_div and details_div.get("data-ad-price"):
        try: 
            return int(details_div["data-ad-price"])
        except ValueError: 
            # print(f"Warning: Could not convert data-ad-price '{details_div['data-ad-price']}' to int.")
            pass # Fall through to other methods if conversion fails
    
    # Fallback method 1: Text content of 'div.price__value.jsPriceValue'
    price_value_div = soup.find("div", class_="price__value jsPriceValue")
    if price_value_div:
        price_text = clean_text(price_value_div.get_text(strip=True))
        if price_text:
            # Remove currency symbols (€), thousands separators (.), and any remaining whitespace
            price_text_cleaned = price_text.replace('€', '').replace('.', '').strip()
            try: 
                return int(price_text_cleaned)
            except ValueError: 
                # print(f"Warning: Could not convert price text (option b) '{price_text_cleaned}' to int.")
                pass
    
    # Fallback method 2: Text content of 'div.toolbar-mobile__price' (often for mobile views)
    toolbar_price_div = soup.find("div", class_="toolbar-mobile__price")
    if toolbar_price_div:
        price_text = clean_text(toolbar_price_div.get_text(strip=True))
        if price_text:
            price_text_cleaned = price_text.replace('€', '').replace('.', '').strip()
            try: 
                return int(price_text_cleaned)
            except ValueError: 
                # print(f"Warning: Could not convert price text (option c) '{price_text_cleaned}' to int.")
                pass
    
    return None # Return None if price couldn't be extracted

def extract_native_id(soup):
    """
    Extracts the website's native advertisement ID (data-ad-id) for the property.

    Args:
        soup (BeautifulSoup): The parsed HTML content of the property page.

    Returns:
        str or None: The native ad ID, or None if not found.
    """
    details_div = soup.find("div", class_="details", attrs={"data-ad-id": True})
    if details_div and details_div.get("data-ad-id"):
        return details_div["data-ad-id"]
    return None

def extract_location_details(soup):
    """
    Extracts barrio (neighborhood) and distrito (district) from the property page.
    Targets a <p> tag usually following an <h1> title, with text like:
    "Opañel (Distrito Carabanchel. Madrid Capital)"

    Args:
        soup (BeautifulSoup): The parsed HTML content of the property page.

    Returns:
        dict: A dictionary with 'barrio' and 'distrito' keys. Values are strings or None.
    """
    barrio = None
    distrito = None

    # Primary strategy: Look for a specific pattern of <h1> followed by <p> within "details__block" divs
    detail_blocks = soup.find_all("div", class_="details__block")
    found_location = False
    for block in detail_blocks:
        h1_tag = block.find("h1")
        # Heuristic to identify the main title <h1> (e.g., contains common sale/rental phrases)
        if h1_tag and (
            " en venta en " in h1_tag.get_text(strip=True).lower() or 
            " en alquiler en " in h1_tag.get_text(strip=True).lower() or # Keep for generality
            len(h1_tag.get_text(strip=True)) > 15 # Assume titles are reasonably long
            ): 
            p_tag = h1_tag.find_next_sibling("p") # The location is often in the <p> right after <h1>
            if p_tag:
                p_text = clean_text(p_tag.get_text(strip=True))
                # Expected pattern: "BarrioName (Distrito DistritoName. Madrid Capital)"
                if p_text and '(' in p_text and 'Distrito' in p_text and 'Madrid Capital' in p_text:
                    parts = p_text.split('(', 1)
                    barrio = parts[0].strip()
                    
                    if len(parts) > 1:
                        in_parenthesis_text = parts[1]
                        # Regex to find "Distrito SomeName" stopping before '.' or ')'
                        distrito_match = re.search(r"Distrito\s+([^.)]+)", in_parenthesis_text)
                        if distrito_match:
                            distrito = distrito_match.group(1).strip()
                    found_location = True # Location found, no need to check other blocks
                    break 
    
    # Fallback strategy: If the primary strategy fails, search more broadly for <p> tags
    # matching the pattern, with a loose check for a preceding <h1>.    
    if not found_location: 
        all_p_tags = soup.find_all("p")
        for p_tag in all_p_tags:
            p_text = clean_text(p_tag.get_text(strip=True))
            if p_text and '(' in p_text and 'Distrito' in p_text and 'Madrid Capital' in p_text:
                prev_sibling = p_tag.find_previous_sibling()
                # Check if this p_tag is likely a subtitle to a preceding h1
                if prev_sibling and prev_sibling.name == 'h1':
                    parts = p_text.split('(', 1)
                    barrio = parts[0].strip()
                    if len(parts) > 1:
                        in_parenthesis_text = parts[1]
                        distrito_match = re.search(r"Distrito\s+([^.)]+)", in_parenthesis_text)
                        if distrito_match:
                            distrito = distrito_match.group(1).strip()
                    break # Found with fallback, stop searching
    
    return {"barrio": barrio, "distrito": distrito}

def extract_features(soup):
    """
    Extracts all property features from the 'Características' (Features) section.
    Features are typically listed as label-value pairs or standalone labels.

    Args:
        soup (BeautifulSoup): The parsed HTML content of the property page.

    Returns:
        dict: A dictionary where keys are feature labels (e.g., "Superficie construida")
              and values are the feature values (str) or True for binary features.
    """
    features_dict = {}
    features_section = soup.find("div", class_="features") # Main container for all features
    if not features_section: 
        return features_dict # Return empty dict if features section not found
    
    feature_elements = features_section.find_all("div", class_="features__feature")
    for fe in feature_elements:
        label_span = fe.find("span", class_="features__label")
        value_span = fe.find("span", class_="features__value")
        
        if label_span:
            # Clean label: remove trailing colons and strip whitespace
            label_text = clean_text(label_span.get_text(strip=True)).replace(':', '').strip()
            
            if value_span: 
                features_dict[label_text] = clean_text(value_span.get_text(strip=True))
            else: 
                # If no specific value_span, the feature might be binary (presence implies True)
                # e.g., "Cocina equipada" where the label itself is the full feature description.
                features_dict[label_text] = True
    return features_dict

def extract_energy_certificate(soup):
    """
    Extracts energy certificate details: main classification, consumption (rating and value),
    and emissions (rating and value).

    Args:
        soup (BeautifulSoup): The parsed HTML content of the property page.

    Returns:
        dict: A dictionary containing energy certificate information.
              Keys: "energy_certificate_main_classification", "energy_consumption_rating",
              "energy_consumption_value", "energy_emissions_rating", "energy_emissions_value".
              Values will be None if specific data is not found.
    """
    energy_data = {
        "energy_certificate_main_classification": None, 
        "energy_consumption_rating": None,
        "energy_consumption_value": None, 
        "energy_emissions_rating": None, 
        "energy_emissions_value": None
    }
    energy_block = soup.find("div", class_="details__block energy-certificate")
    if not energy_block: 
        return energy_data # Return default Nones if the whole block is missing
    
    # Extract main classification text (e.g., "Disponible", "No indicado")
    p_tag_classification = energy_block.find("p")
    if p_tag_classification:
        main_classification_text = clean_text(p_tag_classification.get_text(strip=True))
        if main_classification_text and "Clasificación:" in main_classification_text:
            energy_data["energy_certificate_main_classification"] = main_classification_text.replace("Clasificación:", "").strip()
        elif main_classification_text: # Store raw text if prefix not found but text exists
            energy_data["energy_certificate_main_classification"] = main_classification_text
    
    # Extract detailed Consumo (Consumption) and Emisiones (Emissions) data
    data_divs = energy_block.find_all("div", class_="energy-certificate__data")
    for data_div in data_divs:
        tag_span = data_div.find("span", class_="energy-certificate__tag") # e.g., <span class="...--e">e</span>
        # The descriptive text (e.g., "Consumo: ...") is usually in the next span sibling
        value_info_span = tag_span.find_next_sibling("span") if tag_span else None
        
        if tag_span and value_info_span:
            rating_letter = clean_text(tag_span.get_text(strip=True)).upper() # Get the letter (E, D, etc.)
            # get_text with separator joins text from nested spans correctly
            info_text = clean_text(value_info_span.get_text(separator=" ", strip=True)) 
            
            if "Consumo:" in info_text:
                energy_data["energy_consumption_rating"] = rating_letter
                # Extract the value part after "Consumo:"
                energy_data["energy_consumption_value"] = info_text.split("Consumo:", 1)[-1].strip()
            elif "Emisiones:" in info_text:
                energy_data["energy_emissions_rating"] = rating_letter
                # Extract the value part after "Emisiones:"
                energy_data["energy_emissions_value"] = info_text.split("Emisiones:", 1)[-1].strip()
    
    return energy_data

def extract_description(soup):
    """
    Extracts the property's textual description.
    Handles <br> tags by converting them to newline characters for better readability.

    Args:
        soup (BeautifulSoup): The parsed HTML content of the property page.

    Returns:
        str or None: The cleaned property description, or None if not found.
    """
    description_div = soup.find("div", class_="description__content")
    if description_div:
        text_parts = []
        # Iterate through contents to handle <br> tags explicitly for newlines
        for content_element in description_div.contents:
            if isinstance(content_element, str): # NavigableString
                text_parts.append(str(content_element))
            elif content_element.name == 'br': 
                text_parts.append('\n') # Convert <br> to newline
            else: # Other tags, get their text
                text_parts.append(content_element.get_text(strip=False))
        
        full_description = "".join(text_parts)
        return clean_text(full_description) # Clean up combined text (e.g., multiple spaces)
    return None

# --- Main Detail Scraping Function ---
def scrape_property_details(property_url):
    """
    Fetches and scrapes all defined details for a single property URL.
    Handles potential errors during the scraping of one page.

    Args:
        property_url (str): The URL of the property detail page to scrape.

    Returns:
        dict: A dictionary containing all scraped details for the property.
              Includes 'url', 'scrape_status', and 'scraped_timestamp'.
              Other keys are populated by the extraction helper functions.
    """
    # print(f"Scraping details for: {property_url}") # Uncomment for verbose per-URL logging
    details = {} # Initialize empty dict; URL will be added from the input list
    
    try:
        # Make the HTTP GET request to the property page
        response = requests.get(property_url, headers={'User-Agent': USER_AGENT}, timeout=REQUEST_TIMEOUT_DETAILS) 
        response.raise_for_status() # Check for HTTP errors (4xx or 5xx)
        soup = BeautifulSoup(response.text, "html.parser") # Parse the HTML

        # Call individual extraction functions for each piece of data
        # For RENTAL properties, the price is 'rent_eur_per_month'
        details["rent_eur_per_month"] = extract_price(soup)
        details["property_native_id"] = extract_native_id(soup)
        
        location_info = extract_location_details(soup) # Gets {'barrio': ..., 'distrito': ...}
        details.update(location_info) # Merge location data into the main details dict

        features = extract_features(soup) # Gets a dict of all features
        details.update(features) # Merge features; feature labels become keys

        energy_certificate_info = extract_energy_certificate(soup) # Gets various energy metrics
        details.update(energy_certificate_info) # Merge energy data

        details["description"] = extract_description(soup)
        
        # Record successful scrape and timestamp
        details["scraped_timestamp"] = datetime.now().isoformat()
        details["scrape_status"] = "Success"

    except requests.exceptions.HTTPError as e:
        # Handle HTTP errors (e.g., 404 Not Found, 500 Server Error)
        status_code = e.response.status_code if e.response is not None else "Unknown"
        print(f"HTTP error {status_code} scraping details for {property_url}: {e}")
        details["scrape_status"] = f"HTTP Error: {status_code}"
    except requests.exceptions.RequestException as e:
        # Handle other network-related errors (e.g., timeout, DNS failure)
        print(f"Request error scraping details for {property_url}: {e}")
        details["scrape_status"] = f"Request Error: {type(e).__name__}"
    except Exception as e:
        # Catch any other unexpected errors during parsing or data extraction
        print(f"Unexpected error occurred while scraping details for {property_url}: {e}")
        details["scrape_status"] = f"Unexpected Error: {type(e).__name__}"
        
    return details

# --- Main Execution Block: This code runs when the script is executed directly---
if __name__ == "__main__":
    print("--- pisos.com Scraper: Property Links & Details (RENTAL Listings) ---")
    print(f"Output CSV will be saved to: {OUTPUT_CSV_FILEPATH}")

    # Stage 1: Get all property links and initial geo data
    # This list contains dictionaries like: {'url': ..., 'latitude': ..., 'longitude': ..., 'page_source': ...}
    property_links_info = get_all_property_links_and_geo(PISOS_BASE_URL, INITIAL_LISTING_URL_RENTAL)
    
    if not property_links_info:
        print("No property links found in Stage 1. Exiting.")
    else:
        print(f"\nStage 2: Scraping details for {len(property_links_info)} properties...")
        all_properties_combined_data = [] # List to store the final combined dictionaries for each property
        
        # --- Optional: For testing, process only a small subset of URLs ---
        # To test, uncomment and adjust the slice (e.g., first 5 properties):
        # property_links_info = property_links_info[:5]
        # print(f"--- RUNNING IN TEST MODE: Processing details for only {len(property_links_info)} properties ---")
        # --- End of test mode configuration ---

        # Iterate through each property entry from the input JSON
        for i, link_info_dict in enumerate(property_links_info):
            url = link_info_dict.get("url")
            if not url:
                print(f"Skipping item {i+1} (from Stage 1) due to missing URL: {link_info_dict}")
                # Create a basic record even if URL is missing, to maintain row count if needed
                # or decide to skip entirely.
                error_record = link_info_dict.copy()
                error_record["scrape_status"] = "Missing URL from Stage 1"
                error_record["scraped_timestamp"] = datetime.now().isoformat()
                all_properties_combined_data.append(error_record)
                continue
            
            # Log progress periodically
            if (i + 1) % 10 == 0 or i == 0 or (i + 1) == len(property_links_info):
                # Try to get a short identifier from the URL for logging, fallback if parsing fails
                url_identifier = url.split('/')[-2] if url and len(url.split('/')) > 2 else "Unknown URL"
                print(f"Processing details for property {i+1}/{len(property_links_info)}: {url_identifier}")

            # Scrape details for the current URL
            scraped_details_dict = scrape_property_details(url) 
            
            # Combine the original info from Stage 1 (url, lat, lon, page_source)
            # with the newly scraped details.
            # The .copy() ensures we don't modify the original dict in property_links_info if it's referenced elsewhere.
            combined_record = link_info_dict.copy()
            combined_record.update(scraped_details_dict) # Add/overwrite with new details
            
            all_properties_combined_data.append(combined_record)
            
            time.sleep(POLITE_DELAY_SECONDS) # Polite delay between scraping detail pages
            
        print("\nStage 2: Detail scraping complete.")
        print("Converting all collected data to DataFrame and saving to CSV...")
        
        # Create a Pandas DataFrame from the list of property dictionaries
        df = pd.DataFrame(all_properties_combined_data)
        
        # Define a preferred order for important columns at the beginning of the CSV
        # This makes the output CSV easier to inspect.
        desired_column_order = [
            "url", "property_native_id", "price_eur", 
            "barrio", "distrito", 
            "latitude", "longitude", "page_source", 
            "scrape_status", "scraped_timestamp", "description", 
            "energy_certificate_main_classification", "energy_consumption_rating", "energy_consumption_value",
            "energy_emissions_rating", "energy_emissions_value"
            # Feature columns (e.g., "Superficie construida", "Habitaciones") will be added after these
        ]
        
        # Reorder columns: put desired columns first, then all others alphabetically
        front_columns = [col for col in desired_column_order if col in df.columns]
        # Get remaining columns (mostly features) and sort them alphabetically for consistency
        other_columns = sorted([col for col in df.columns if col not in front_columns])
        
        # Concatenate and reindex the DataFrame
        df = df[front_columns + other_columns]

        # --- Ensure the output directory exists before saving the CSV ---
        print(f"\nEnsuring output directory exists: {RAW_DATA_DIR}")
        try:
            RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
            print(f"Output directory '{RAW_DATA_DIR}' is ready.")
        except OSError as e:
            print(f"Error creating directory {RAW_DATA_DIR}. Saving to current directory. Error: {e}")
            OUTPUT_CSV_FILEPATH = Path(BASE_OUTPUT_CSV_FILENAME) # Fallback to current directory if RAW_DATA_DIR creation fails

        # Save the DataFrame to a CSV file
        try:
            df.to_csv(OUTPUT_CSV_FILEPATH, index=False, encoding='utf-8')
            print(f"Successfully saved data for {len(df)} properties to {OUTPUT_CSV_FILEPATH}")
        except Exception as e:
            print(f"Error saving DataFrame to CSV file {OUTPUT_CSV_FILEPATH}: {e}")

    print("\n--- Script Finished ---")