import cloudscraper
import json
import random
import csv
import datetime
import time
from colorama import Fore, Style, init


init(autoreset=True)

def get_page_response(url):
    """
    Fetch the page response from the given URL using cookies and proxies.
    
    Args:
        url (str): The URL to fetch the page from.

    Returns:
        response: The response object from the request.
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
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://google.com',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Sec-CH-UA': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"',
    }

    try:

        response = scraper.get(url, headers=headers, cookies=cookies, proxies=proxies)
        return response.json()
    except Exception as e:
        print(f"Error fetching page response: {e}")
        return None

def fetch_wallet_data(wallet):
    url = f"https://gmgn.ai/defi/quotation/v1/smartmoney/sol/walletNew/{wallet}?period=30d"
    response = get_page_response(url)
    
    if response and response.get('code') == 0:
        data = response.get("data", {})
        

        sol_balance = data.get("sol_balance")
        pnl_7d = data.get("pnl_7d")
        pnl_30d = data.get("pnl_30d")
        total_profit = data.get("total_profit")
        winrate = data.get("winrate")
        realized_profit_7d = data.get("realized_profit_7d")
        realized_profit_30d = data.get("realized_profit_30d")
        buy_30d = data.get("buy_30d")
        sell_30d = data.get("sell_30d")
        buy_7d = data.get("buy_7d")
        sell_7d = data.get("sell_7d")
        token_avg_cost = data.get("token_avg_cost", 0)
        token_sold_avg_profit = data.get("token_sold_avg_profit", 0)
        token_num = data.get("token_num", 0)

        last_active_timestamp = data.get("last_active_timestamp")
        if last_active_timestamp:
            last_active_time = datetime.datetime.fromtimestamp(last_active_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        else:
            last_active_time = "N/A"

        return {
            "wallet": wallet,
            "sol_balance": sol_balance,
            "pnl_7d": pnl_7d * 100 if pnl_7d is not None else None,
            "pnl_30d": pnl_30d * 100 if pnl_30d is not None else None,
            "total_profit": total_profit,
            "winrate": winrate * 100 if winrate is not None else None,
            "realized_profit_7d": realized_profit_7d,
            "realized_profit_30d": realized_profit_30d,
            "buy_30d": buy_30d,
            "sell_30d": sell_30d,
            "buy_7d": buy_7d,
            "sell_7d": sell_7d,
            "last_active_time": last_active_time,
            "token_avg_cost": token_avg_cost,
            "token_sold_avg_profit": token_sold_avg_profit,
            "token_num": token_num
        }
    else:
        print(f"Failed to fetch data for wallet {wallet}: {response.get('msg') if response else 'No response'}")
        return None

def determine_tag(total_profit, token_avg_cost, token_sold_avg_profit, token_num):
    ratio = (token_sold_avg_profit / token_avg_cost) if token_avg_cost > 0 else 0
    if token_num > 500:
        return "MEV Botter"
    elif total_profit <= 0 or token_avg_cost == 0 or token_sold_avg_profit == 0:
        return "Newbie"
    elif ratio < 1:
        return "Pumper"
    elif ratio >= 1:
        return "Insider"
    return "N/A"

def read_makers_file(filepath):
    with open(filepath, 'r') as file:
        return file.read().split(';')

def write_wallet_data_to_csv(wallet_data, output_file):
    with open(output_file, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[
            "wallet", "sol_balance", "pnl_7d", "pnl_30d", "total_profit", "winrate",
            "realized_profit_7d", "realized_profit_30d", "buy_30d", "sell_30d", 
            "buy_7d", "sell_7d", "last_active_time", "token_avg_cost", 
            "token_sold_avg_profit", "token_num", "tag"
        ])
        
        if csvfile.tell() == 0:
            writer.writeheader()
        
        writer.writerow(wallet_data)

def print_wallet_info(wallet, winrate, tag):
    if tag == "Newbie" and winrate > 60:
        color = Fore.LIGHTYELLOW_EX
    elif tag == "Newbie" and winrate <= 60:
        color = Fore.RED
    elif tag == "MEV Botter":
        color = Fore.RED
    elif tag in ["Pumper", "Insider"]:
        color = Fore.GREEN
    else:
        color = Fore.WHITE

    print(f"{color}Address: {wallet}, Winrate: {winrate:.2f}%, Tag: {tag}{Style.RESET_ALL}")

def monitor_wallets(makers_file, output_file, check_interval=60):
    processed_wallets = set()

    while True:
        wallets = read_makers_file(makers_file)

        for wallet in wallets:
            wallet = wallet.strip()
            if wallet and wallet not in processed_wallets:
                wallet_data = fetch_wallet_data(wallet)
                if wallet_data:

                    tag = determine_tag(
                        wallet_data.get("total_profit", 0) or 0,
                        wallet_data.get("token_avg_cost", 0) or 0,
                        wallet_data.get("token_sold_avg_profit", 0) or 0,
                        wallet_data.get("token_num", 0) or 0
                    )
                    winrate = wallet_data.get("winrate", 0) or 0
                    wallet_data["tag"] = tag

                    
                    print_wallet_info(wallet, winrate, tag)

                   
                    write_wallet_data_to_csv(wallet_data, output_file)

                    
                    processed_wallets.add(wallet)

        
        time.sleep(check_interval)

if __name__ == "__main__":
    makers_file = "makers.txt"
    output_file = "wallet_data.csv"

    
    monitor_wallets(makers_file, output_file)
