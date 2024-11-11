import cloudscraper
import json
import random
import time

def get_page_response(url):
    """
    Fetch the page response from the given URL using cookies and proxies.
    
    Args:
        url (str): The URL to fetch the page from.

    Returns:
        response: The JSON response object from the request.
    """
    cookies_file_path = r''
    proxies_file_path = r''

    with open(cookies_file_path, 'r') as file:
        cookies_list = json.load(file)

    cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}

    with open(proxies_file_path, 'r') as file:
        proxies_list = file.readlines()

    proxy = random.choice(proxies_list).strip()
    ip, port, user, password = proxy.split(':')

    proxies = {
        'http': f'http://{user}:{password}@{ip}:{port}',
        'https': f'http://{user}:{password}@{ip}:{port}',
    }

    scraper = cloudscraper.create_scraper()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://google.com',
    }

    try:
        response = scraper.get(url, headers=headers, cookies=cookies, proxies=proxies)

        if response.status_code == 200:
            print(f"Raw response: {response.text[:200]}") 
            if response.text.strip():  
                return response.json()
            else:
                print("Error: Received empty response from the server.")
                return None
        else:
            print(f"Error: Unexpected status code {response.status_code}. Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"Error fetching page response: {e}")
        return None

def extract_addresses(response):
    """
    Extract all addresses from the response JSON.
    
    Args:
        response (dict): The JSON response from the request.

    Returns:
        list: A list of addresses.
    """
    addresses = []
    if response and response.get('code') == 0:
        pumps = response.get('data', {}).get('pumps', [])
        addresses = [pump['address'] for pump in pumps if 'address' in pump]
    
    return addresses

def load_existing_addresses(file_path):
    """
    Load the existing addresses from the specified file.
    
    Args:
        file_path (str): The path to the file containing addresses.

    Returns:
        set: A set of existing addresses.
    """
    try:
        with open(file_path, 'r') as file:
            return set(file.read().splitlines())
    except FileNotFoundError:
        return set()

def save_new_addresses(addresses, file_path):
    """
    Save new addresses to the specified file and print a notification.
    
    Args:
        addresses (list): A list of new addresses to save.
        file_path (str): The path to the file where addresses will be saved.
    """
    with open(file_path, 'a') as file:
        for address in addresses:
            file.write(f"{address}\n")
            print(f"Stored new address: {address}")

def print_and_track_new_addresses(new_addresses, printed_addresses):
    """
    Print new addresses and track them to avoid reprinting.
    
    Args:
        new_addresses (list): A list of new addresses.
        printed_addresses (set): A set of already printed addresses.
    """
    for address in new_addresses:
        if address not in printed_addresses:
            print(f"New Address: {address}")
            printed_addresses.add(address)

def main():
    url = "https://gmgn.ai/defi/quotation/v1/rank/sol/pump_ranks/1h?new_creation=%7B%22filters%22:[],%22limit%22:80%7D&pump=%7B%22filters%22:[],%22limit%22:80%7D&completed=%7B%22filters%22:[],%22limit%22:60%7D"
    file_path = r""
    
    existing_addresses = load_existing_addresses(file_path)
    printed_addresses = set(existing_addresses)
    print(f"Loaded {len(existing_addresses)} existing addresses.")

    while True:
        response = get_page_response(url)
        
        if response:
            new_addresses = extract_addresses(response)
            new_unique_addresses = [addr for addr in new_addresses if addr not in existing_addresses]

            if new_unique_addresses:
                print_and_track_new_addresses(new_unique_addresses, printed_addresses)
                save_new_addresses(new_unique_addresses, file_path)
                existing_addresses.update(new_unique_addresses)
            else:
                print("No new addresses found.")
        else:
            print("Failed to retrieve data.")

        time.sleep(300)

if __name__ == "__main__":
    main()
