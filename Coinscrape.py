import discord
from discord.ext import commands
from discord import app_commands
import requests
import json
import csv
import io
import os

TOKEN = ''

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")
    print(f"Connected to {len(bot.guilds)} guilds.")

def fetch_wallet_data(wallet):
    base_url = "https://gmgn.ai/defi/quotation/v1/smartmoney/sol/walletNew/{}?period=30d"
    url = base_url.format(wallet)
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        response_json = response.json()

        print(f"Data fetched from API for wallet {wallet}:\n{response_json}\n")

        data = response_json.get("data", {})
        return {
            "wallet": wallet,
            "sol_balance": data.get("sol_balance"),
            "pnl_7d": data.get("pnl_7d") * 100 if data.get("pnl_7d") is not None else None,
            "pnl_30d": data.get("pnl_30d") * 100 if data.get("pnl_30d") is not None else None,
            "total_profit": data.get("total_profit"),
            "winrate": data.get("winrate") * 100 if data.get("winrate") is not None else None,
            "realized_profit_7d": data.get("realized_profit_7d"),
            "realized_profit_30d": data.get("realized_profit_30d"),
            "buy_30d": data.get("buy_30d"),
            "sell_30d": data.get("sell_30d"),
            "buy_7d": data.get("buy_7d"),
            "sell_7d": data.get("sell_7d")
        }
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return {"wallet": wallet, "error": str(e)}

@bot.tree.command(name="walletcheck", description="Check the wallet information for one or multiple wallets")
@app_commands.describe(wallets="The wallet address or multiple addresses separated by ';'")
async def walletcheck(interaction: discord.Interaction, wallets: str):
    await interaction.response.defer()

    wallet_list = wallets.split(';')
    
    if len(wallet_list) > 100:
        await interaction.followup.send("You can only check up to 100 wallets at once. Please reduce the number of wallets.")
        return
    
    wallet_data_list = []

    for wallet in wallet_list:
        wallet_data = fetch_wallet_data(wallet.strip())
        wallet_data_list.append(wallet_data)


    csv_output = io.StringIO()
    csv_writer = csv.DictWriter(csv_output, fieldnames=[
        "wallet", "sol_balance", "pnl_7d", "pnl_30d", "total_profit", "winrate",
        "realized_profit_7d", "realized_profit_30d", "buy_7d", "sell_7d", "buy_30d", "sell_30d"
    ])
    
    csv_writer.writeheader()
    for wallet_data in wallet_data_list:
        csv_writer.writerow(wallet_data)
    
    csv_output.seek(0)


    file = discord.File(fp=io.BytesIO(csv_output.getvalue().encode('utf-8')), filename="wallet_check.csv")
    await interaction.followup.send("Here is the CSV file with the wallet data:", file=file)

def fetch_token_data(token_address):
    base_url = 'https://gmgn.ai/defi/quotation/v1/tokens/sol/{}'
    url = base_url.format(token_address)
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return {"error": str(e)}

@bot.tree.command(name="coinscrape", description="Scrape wallet addresses for specified coins and save to a text file.")
@app_commands.describe(coins="The coins to scrape wallet addresses for, separated by commas")
@commands.has_role(1267726167671046239)  
async def coinscrape(interaction: discord.Interaction, coins: str):
    await interaction.response.defer()

    coin_list = [coin.strip() for coin in coins.split(';')]  
    
    for coin in coin_list:

        url = f"https://gmgn.ai/defi/quotation/v1/tokens/top_buyers/sol/{coin}"

        try:

            response = requests.get(url)
            
            
            print(f"Response for {coin}:")
            print(response.text)  

            if response.status_code == 200:
                
                token_data = response.json()

                holder_info = token_data.get("data", {}).get("holders", {}).get("holderInfo", [])
                
                wallet_addresses = [holder.get("wallet_address") for holder in holder_info if holder.get("wallet_address")]

                if wallet_addresses:
                    formatted_addresses = ";".join(wallet_addresses)
                    
                    filename = f"{coin}_wallet_addresses.txt"
                    with open(filename, "w") as file:
                        file.write(formatted_addresses)

                    try:
                        await interaction.user.send(f"Here are the wallet addresses for {coin}:", file=discord.File(filename))
                        await interaction.followup.send(f"Wallet addresses for {coin} have been successfully fetched and sent to your DM!", ephemeral=True)
                    except discord.Forbidden:
                        await interaction.followup.send("I couldn't DM you. Please check your privacy settings.", ephemeral=True)
                    
                    os.remove(filename)
                else:
                    await interaction.followup.send(f"No wallet addresses found for {coin}.", ephemeral=True)
            else:
                await interaction.followup.send(f"Failed to retrieve data for {coin}. Status code: {response.status_code}", ephemeral=True)
        
        except requests.exceptions.RequestException as e:
            await interaction.followup.send(f"An error occurred while fetching data for {coin}: {e}", ephemeral=True)

@coinscrape.error
async def coinscrape_error(interaction: discord.Interaction, error):
    if isinstance(error, commands.MissingRole):
        await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)

def format_number(n):
    try:
        n = float(n)
        if n >= 1_000_000_000:
            return f"{n/1_000_000_000:.2f}B"
        elif n >= 1_000_000:
            return f"{n/1_000_000:.2f}M"
        elif n >= 1_000:
            return f"{n/1_000:.2f}k"
        else:
            return f"{n:.2f}"
    except (ValueError, TypeError):
        return "N/A"

def format_percentage(n):
    try:
        return f"{float(n) * 100:.2f}%"
    except (ValueError, TypeError):
        return "N/A"

def yes_no(value):
    return "Yes" if value == 1 else "No"

@bot.tree.command(name="scan", description="Fetches and displays token data.")
@app_commands.describe(token="The token address to scan")
async def scan(interaction: discord.Interaction, token: str):
    base_url = 'https://gmgn.ai/defi/quotation/v1/tokens/sol/{}'
    url = base_url.format(token)
    
    try:
        response = requests.get(url)

        if response.status_code == 200:
            response_data = response.json()


            token_data = response_data.get("data", {}).get("token", {})
            token_address = token_data.get("address", "N/A")
            creator_address = token_data.get("creator_address", "N/A")
            token_logo = token_data.get("logo", "")

            price = float(token_data.get("price", 0))
            formatted_price = f"{price:.8f}".rstrip('0').rstrip('.') if price < 1 else f"{price:.2f}"

            embed = discord.Embed(title=f"{token_data.get('name')} @ {token_data.get('symbol')}", color=0x1e1e2e)
            embed.set_thumbnail(url=token_logo)
            embed.set_footer(text="Data provided by ", icon_url="")

    
            embed.add_field(name="🔗 Address", value=f"{token_address}", inline=False)
            embed.add_field(name="👤 Creator", value=f"{creator_address}", inline=False)

            embed.add_field(name="💵 USD", value=f"${formatted_price}", inline=True)
            embed.add_field(name="💰 FDV", value=f"${format_number(token_data.get('fdv'))}", inline=True)
            embed.add_field(name="🔒 Liquidity", value=f"${format_number(token_data.get('liquidity'))}", inline=True)
            
            volume_1h = format_number(token_data.get('volume_1h', 0))
            volume_6h = format_number(token_data.get('volume_6h', 0))
            volume_24h = format_number(token_data.get('volume_24h', 0))

            embed.add_field(name="⏱ Volume (1h)", value=f"{volume_1h}", inline=True)
            embed.add_field(name="⏱ Volume (6h)", value=f"{volume_6h}", inline=True)
            embed.add_field(name="⏱ Volume (24h)", value=f"{volume_24h}", inline=True)

            top_10_holder_rate = format_percentage(token_data.get('top_10_holder_rate', 0))
            renounced_mint = yes_no(token_data.get('renounced_mint', 0))
            renounced_freeze_account = yes_no(token_data.get('renounced_freeze_account', 0))
            burn_ratio = format_percentage(token_data.get('burn_ratio', 0))
            burn_status = token_data.get('burn_status', 'N/A')
            holder_count = format_number(token_data.get('holder_count', 0))

            embed.add_field(name="🔟 Top 10 Holder Rate", value=top_10_holder_rate, inline=True)
            embed.add_field(name="🔓 Renounced Mint", value=renounced_mint, inline=True)
            embed.add_field(name="❄️ Renounced Freeze", value=renounced_freeze_account, inline=True)
            embed.add_field(name="🔥 Burn Ratio", value=burn_ratio, inline=True)
            embed.add_field(name="🔥 Burn Status", value=burn_status, inline=True)
            embed.add_field(name="👥 Holder Count", value=holder_count, inline=True)

            website = token_data.get("social_links", {}).get("website", "N/A")
            telegram = token_data.get("social_links", {}).get("telegram", "N/A")
            twitter_username = token_data.get("social_links", {}).get("twitter_username", "N/A")

            if website != "N/A":
                website_link = f"[Website]({website})"
            else:
                website_link = "N/A"

            if telegram != "N/A":
                telegram_link = f"[Telegram]({telegram})"
            else:
                telegram_link = "N/A"

            if twitter_username != "N/A":
                twitter_link = f"[Twitter](https://x.com/{twitter_username})"
            else:
                twitter_link = "N/A"

            embed.add_field(name="🌐 Website", value=website_link, inline=True)
            embed.add_field(name="📲 Telegram", value=telegram_link, inline=True)
            embed.add_field(name="🐦 Twitter", value=twitter_link, inline=True)


            bullx_link = f"[BullX](https://bullx.io/terminal?chainId=1399811149&address={token_address})"
            dexscreener_link = f"[DexScreener](https://dexscreener.com/solana/{token_address})"
            pump_link = f"[Pump](https://pump.fun/{token_address})"
            solscan_link = f"[SolScan](https://solscan.io/token/{token_address})"
            telegram_bot_link = f"[Trojan Bot](https://t.me/paris_trojanbot?start=r-matismrd-{token_address})"

            embed.add_field(name="🔗 Quick Access", value=f"{bullx_link} | {dexscreener_link} | {pump_link} | {solscan_link} | {telegram_bot_link}", inline=False)

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"Failed to retrieve data. HTTP Status code: {response.status_code}")
    
    except requests.exceptions.RequestException as e:
        await interaction.response.send_message(f"An error occurred: {e}")

bot.run(TOKEN)
