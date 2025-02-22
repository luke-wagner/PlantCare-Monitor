'''
File: fetch_plant_data.py
Author: Luke Wagner

Connects to greg.app site and fetches plant data for the user, stores to db
'''

import socket
import ssl
import re
import gc

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
        chunk = response.raw.read(2048)
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
    plant_name = ""
    open_h1 = article_content.find("<h1")
    if open_h1 != -1:
        tag_close = article_content.find(">", open_h1)
        if tag_close != -1:
            close_h1 = article_content.find("</h1>", tag_close)
            if close_h1 != -1:
                plant_name = article_content[tag_close + 1:close_h1].strip()
                search_index = close_h1 + len("</h1>")
            else:
                search_index = tag_close + 1
        else:
            search_index = 0
    else:
        search_index = 0

    # Extract plant species from the first <h3> tag after the plant name
    plant_type = ""
    open_h3 = article_content.find("<h3", search_index)
    if open_h3 != -1:
        tag_close = article_content.find(">", open_h3)
        if tag_close != -1:
            close_h3 = article_content.find("</h3>", tag_close)
            if close_h3 != -1:
                h3_raw = article_content[tag_close + 1:close_h3].strip()
                plant_type = strip_tags(h3_raw)
    return plant_name, plant_type


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
        print("\nFetching plant page:", link)
        print("Free memory:", gc.mem_free())
        plant_html = process_plant_page(link)
        plant_name, plant_species = extract_plant_data(plant_html)
        if plant_name and plant_species:
            print("Plant Name:   ", plant_name)
            print("Plant Species:", plant_species)
        else:
            print("Error: Could not extract plant details from", link)
            
        del plant_html
        gc.collect()


if __name__ == "__main__":
    main()
