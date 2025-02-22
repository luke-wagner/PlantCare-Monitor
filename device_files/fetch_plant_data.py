'''
File: fetch_plant_data.py
Author: Luke Wagner

Connects to greg.app site and fetches plant data for the user, stores to db
'''

from machine import RTC # for getting current time
import socket
import ssl
import re
import gc
import json

# Establish connection to the wifi
from wifi import Connection
connection = Connection()

import urequests
import config  # Ensure config.py defines USERNAME = "your_username_here"


def process_plant_chunk(chunk):
    """Decode a chunk (UTF-8) and return it if it contains an <h1> tag."""
    try:
        chunk_str = chunk.decode('utf-8')
    except UnicodeDecodeError:
        return None
    return chunk_str if "<h1" in chunk_str else None


def process_plant_page(url):
    """
    Fetch a plant page in streaming mode and return the first chunk that 
    contains an <h1> tag.
    """
    response = urequests.get(url, stream=True)
    while True:
        chunk = response.raw.read(4096) # 4096 bytes should be enough to grab all useful info
        if not chunk:
            break
        data = process_plant_chunk(chunk)
        if data is not None:
            response.close()
            return data
    response.close()
    return None


def fetch_url(url):
    """Fetch the URL and return its HTML content."""
    response = urequests.get(url)
    html = response.text
    response.close()
    return html


def find_plant_links(html, username):
    """
    Extract plant links from HTML by locating occurrences of the user's
    plant path and extracting the following 8-character plant ID.
    """
    links = []
    plant_ids = []
    start = 0
    search_str = f"{username}/plants/"
    while True:
        pos = html.find(search_str, start)
        if pos == -1:
            break
        pos += len(search_str)
        plant_id = html[pos:pos + 8]
        plant_ids.append(plant_id)
        start = pos + 8

    print("Found plant IDs:", plant_ids)
    for plant_id in plant_ids:
        link = f"http://greg.app/{username.lower()}/plants/{plant_id}/"
        links.append(link)
    return links


def strip_tags(text):
    """Remove HTML tags from text."""
    result = []
    in_tag = False
    for ch in text:
        if ch == '<':
            in_tag = True
            continue
        if ch == '>':
            in_tag = False
            continue
        if not in_tag:
            result.append(ch)
    return ''.join(result).strip()


def extract_plant_data(html):
    """
    Extract the plant name and species from HTML. The function locates
    the <article> element with id="plant-profile" and then extracts the first 
    <h1> tag as the name and the first <h3> tag as the species.
    """

    return_data = {}

    # Locate the <article> tag with id="plant-profile"
    index = 0
    while True:
        start_index = html.find("<article", index)
        if start_index == -1:
            return None, None  # Article tag not found
        end_of_tag = html.find(">", start_index)
        if end_of_tag == -1:
            return None, None  # Malformed HTML
        opening_tag = html[start_index:end_of_tag + 1]
        if 'id="plant-profile"' in opening_tag:
            break
        index = end_of_tag + 1

    article_content = html[end_of_tag + 1:]

    # Extract plant name from the first <h1> tag
    open_h1 = article_content.find("<h1")
    if open_h1 != -1:
        tag_close = article_content.find(">", open_h1)
        if tag_close != -1:
            close_h1 = article_content.find("</h1>", tag_close)
            if close_h1 != -1:
                plant_name = article_content[tag_close + 1:close_h1].strip()
                return_data["plant_name"] = plant_name
                search_index = close_h1 + len("</h1>")
            else:
                search_index = tag_close + 1
        else:
            search_index = 0
    else:
        search_index = 0

    # Extract plant species from the first <h3> tag after the plant name
    open_h3 = article_content.find("<h3", search_index)
    if open_h3 != -1:
        tag_close = article_content.find(">", open_h3)
        if tag_close != -1:
            close_h3 = article_content.find("</h3>", tag_close)
            if close_h3 != -1:
                h3_raw = article_content[tag_close + 1:close_h3].strip()
                plant_type = strip_tags(h3_raw)
                return_data["plant_type"] = plant_type
                search_index = close_h3 + len("</h3>")

    # Next extract all misc plant details, keep looping until all found
    while True:
        # Find the next plant-detail div
        div_start = html.find('<div class="plant-detail">', search_index)
        if div_start == -1:
            break
            
        # Find the closing div
        div_end = html.find('</div>', div_start)
        if div_end == -1:
            break
            
        # Extract the div content
        div_content = html[div_start:div_end]
        
        # Find the image tag
        img_tag_start = div_content.find('<img')
        if img_tag_start != -1:
            img_tag_end = div_content.find('>', img_tag_start)
            if img_tag_end != -1:
                img_tag = div_content[img_tag_start:img_tag_end + 1]
                
                # Try to find src attribute
                src_start = img_tag.find('src="')
                if src_start != -1:
                    src_start += len('src="')
                    src_end = img_tag.find('"', src_start)
                    if src_end != -1:
                        img_path = img_tag[src_start:src_end]
                        identifier = img_path.split('/')[-1].split('.')[0]
                
                # If no src found or if identifier is empty, try alt attribute
                if 'identifier' not in locals() or not identifier:
                    alt_start = img_tag.find('alt="')
                    if alt_start != -1:
                        alt_start += len('alt="')
                        alt_end = img_tag.find('"', alt_start)
                        if alt_end != -1:
                            identifier = img_tag[alt_start:alt_end].replace('-', '_')
                
                # Find the span content
                span_start = div_content.find('<span>')
                if span_start != -1:
                    span_start += len('<span>')
                    span_end = div_content.find('</span>', span_start)
                    if span_end != -1:
                        value = div_content[span_start:span_end].strip()
                        return_data[identifier] = value
        
        # Move search position to after this div
        search_index = div_end + 1

    return return_data


def write_plant_data_to_json(plant_data, plant_id, filename="plant_data.json"):
    """
    Takes a dictionary of plant data and appends it to a JSON file with a timestamp.
    Modified for MicroPython compatibility.
    
    Args:
        plant_data (dict): Dictionary containing plant information
        filename (str): Name of the output JSON file (default: "plant_data.json")
        
    Returns:
        None
    """
    # Get current time from RTC
    rtc = RTC()
    current_time = rtc.datetime()
    timestamp = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        current_time[0],  # year
        current_time[1],  # month
        current_time[2],  # day
        current_time[4],  # hours
        current_time[5],  # minutes
        current_time[6]   # seconds
    )
    
    # Create the new entry
    new_entry = {
        "plant_id": plant_id,
        "timestamp": timestamp,
        "data": plant_data
    }
    
    try:
        # Try to read existing data
        try:
            with open(filename, 'r') as f:
                content = f.read()
                if content:
                    existing_data = json.loads(content)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
                else:
                    existing_data = []
        except (OSError, ValueError):
            existing_data = []
        
        # Append new entry
        existing_data.append(new_entry)
        
        # Write back to file
        with open(filename, 'w') as f:
            f.write(json.dumps(existing_data))
            
    except OSError as e:
        print("Error writing to file:", str(e))

def main():
    username = config.USERNAME
    username_lower = username.lower()
    base_url = f"http://greg.app/{username_lower}/"
    print("Fetching main page:", base_url)
    
    main_html = fetch_url(base_url)
    plant_links = find_plant_links(main_html, username)
    
    del main_html  # Free memory
    gc.collect()

    for link in plant_links:
        plant_id = link.split("/")[-2] # Grab the plant id from the full url

        print("\nFetching plant page:", link)
        print("Free memory:", gc.mem_free())
        plant_html = process_plant_page(link)
        plant_info = extract_plant_data(plant_html)
        if plant_info is not None and plant_info != {}:
            print("Plant info:")
            for key, value in plant_info.items():
                print(f"- {key}: {value}")
        else:
            print("Error: Could not extract plant details from", link)
            
        write_plant_data_to_json(plant_info, plant_id)

        del plant_html
        gc.collect()


if __name__ == "__main__":
    main()

