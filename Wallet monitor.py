import cloudscraper
import json
import time
import requests
import csv
from datetime import datetime, timezone
from threading import Thread


DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/'


current_proxy_index = 0


wallet_pseudonyms = {
    'wallet_address_1': '1',
    'wallet_address_2': '2',
    'wallet_address_3': '3',
    'wallet_address_4': '4',
    'wallet_address_5': '5',
    'wallet_address_6': '6',
    'wallet_address_7': '7',
    'wallet_address_8': '8',
    'wallet_address_9': '9',
    'wallet_address_10': '10',
   
}


def load_valid_proxy(proxies_list):
    global current_proxy_index
    while True:
        proxy = proxies_list[current_proxy_index].strip()
        parts = proxy.split(':')

        current_proxy_index = (current_proxy_index + 1) % len(proxies_list)

        if len(parts) == 4:  
            ip, port, user, password = parts
            return {
                'http': f'http://{user}:{password}@{ip}:{port}',
                'https': f'http://{user}:{password}@{ip}:{port}',
            }
        elif len(parts) == 2:
            ip, port = parts
            return {
                'http': f'http://{ip}:{port}',
                'https': f'http://{ip}:{port}',
            }
        else:
            print(f"Invalid proxy format, skipping: {proxy}")
            continue


def load_cookies_and_proxies():
    cookies_file_path = r''
    proxies_file_path = r''

    with open(cookies_file_path, 'r') as file:
        cookies_list = json.load(file)
    cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}

    with open(proxies_file_path, 'r') as file:
        proxies_list = file.readlines()

    return cookies, proxies_list

def get_page_response(url, cookies, proxies_list):
    proxies = load_valid_proxy(proxies_list)

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

    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] Sending request to {url} using proxy: {proxies['http'].split('@')[-1]}")

    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, headers=headers, cookies=cookies, proxies=proxies)

        if response.status_code == 200:
            print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] Received response from {url}")
            return response.json()
        else:
            print(f"Error: Received status code {response.status_code} with content: {response.content}")
            return None
    except Exception as e:
        print(f"Error fetching page response: {e}")
        return None

def log_transaction_to_csv(activity, additional_data, pseudonym):
    filename = "transactions_log.csv"
    file_exists = False

    try:
        file_exists = open(filename, 'r')
    except FileNotFoundError:
        pass

    with open(filename, 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'pseudonym', 'event_type', 'token_name', 'token_symbol', 'token_amount', 'quote_amount', 'cost_usd', 'price_usd', 'market_cap', 'volume_5m', 'top_10_holder_rate', 'telegram']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            'timestamp': datetime.fromtimestamp(activity['timestamp'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
            'pseudonym': pseudonym,
            'event_type': activity['event_type'],
            'token_name': activity['token']['name'],
            'token_symbol': activity['token']['symbol'],
            'token_amount': activity['token_amount'],
            'quote_amount': activity['quote_amount'],
            'cost_usd': activity['cost_usd'],
            'price_usd': activity['price'],
            'market_cap': additional_data['market_cap'],
            'volume_5m': additional_data['volume_5m'],
            'top_10_holder_rate': additional_data['top_10_holder_rate'] * 100,
            'telegram': additional_data['telegram']
        })


def send_discord_notification(activity, additional_data, pseudonym):
    token_address = activity['token_address']

    bullx_link = f"[Bullx](https://bullx.io/terminal?chainId=8453&address={token_address})"
    dex_screener_link = f"[Dex Screener](https://dexscreener.com/solana/{token_address})"
    quick_task_text = f"{bullx_link} | {dex_screener_link}"

    embed = {
        "title": f"💸 New {activity['event_type'].capitalize()} Transaction by {pseudonym}!",
        "description": f"**Token:** {activity['token']['name']} ({activity['token']['symbol']})",
        "color": 0x00ff00 if activity['event_type'] == "buy" else 0xff0000,
        "fields": [
            {"name": "💰 Amount", "value": f"{activity['token_amount']} {activity['token']['symbol']}", "inline": True},
            {"name": "💵 Quote Amount", "value": f"{activity['quote_amount']} SOL", "inline": True},
            {"name": "💲 Cost in USD", "value": f"${activity['cost_usd']}", "inline": True},
            {"name": "📈 Price per Token (USD)", "value": f"{float(activity['price']):.12f}", "inline": True},
            {"name": "⏰ Timestamp", "value": datetime.fromtimestamp(activity['timestamp'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'), "inline": False},
            {"name": "💹 Market Cap", "value": f"${additional_data['market_cap']:,}", "inline": True},
            {"name": "📊 Volume (5m)", "value": f"${additional_data['volume_5m']:,}", "inline": True},
            {"name": "🏦 Top 10 Holder Rate", "value": f"{additional_data['top_10_holder_rate'] * 100:.2f}%", "inline": True},
            {"name": "📱 Telegram", "value": f"[Join Telegram]({additional_data['telegram']})", "inline": True},
            {"name": "🔧 Quick Task", "value": quick_task_text, "inline": False}
        ],
        "thumbnail": {"url": activity['token']['logo']},
        "image": {"url": ""}}

    data = {
        "username": "Transaction Monitor",
        "embeds": [embed]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        if response.status_code == 204:
            print("Notification sent successfully.")
        else:
            print(f"Failed to send notification: {response.status_code}")
    except Exception as e:
        print(f"Error sending Discord notification: {e}")


def get_additional_token_data(token_address, cookies, proxies_list):
    url = f"https://gmgn.ai/defi/quotation/v1/tokens/sol/{token_address}"
    response = get_page_response(url, cookies, proxies_list)
    if response and response['code'] == 0:
        data = response['data']['token']
        return {
            'market_cap': data['market_cap'],
            'volume_5m': data['volume_5m'],
            'top_10_holder_rate': data['top_10_holder_rate'],
            'telegram': data['social_links']['telegram'] or "No Telegram Link"
        }
    return {}


def monitor_wallet(wallet, cookies, proxies_list, baseline_time, notified_hashes):
    url = f'https://gmgn.ai/defi/quotation/v1/wallet_activity/sol?type=buy&type=sell&wallet={wallet}'

    pseudonym = wallet_pseudonyms.get(wallet, f"User_{wallet[:6]}")

    while True:
        response = get_page_response(url, cookies, proxies_list)
        if response and response['code'] == 0:
            activities = response['data']['activities']
            for activity in activities:
                transaction_time = datetime.fromtimestamp(activity['timestamp'], tz=timezone.utc)
                if transaction_time > baseline_time and activity['tx_hash'] not in notified_hashes:
                    additional_data = get_additional_token_data(activity['token_address'], cookies, proxies_list)
                    send_discord_notification(activity, additional_data, pseudonym)
                    log_transaction_to_csv(activity, additional_data, pseudonym)
                    notified_hashes.add(activity['tx_hash'])

        time.sleep(30)


def load_wallets_from_file(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file.readlines()]

def monitor_all_wallets():
    wallet_file = r''
    cookies, proxies_list = load_cookies_and_proxies()
    wallets = load_wallets_from_file(wallet_file)

    baseline_time = datetime.now(timezone.utc)
    notified_hashes = set()

    threads = []

    for wallet in wallets:
        thread = Thread(target=monitor_wallet, args=(wallet, cookies, proxies_list, baseline_time, notified_hashes))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    monitor_all_wallets()
