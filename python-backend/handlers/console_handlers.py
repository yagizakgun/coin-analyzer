import logging

# Functions in this module handle user interface elements, like displaying lists
# and getting validated user input from the console.

def display_coin_selection_lists(top_market_cap, top_volume, top_gainers, top_decliners, default_top_n_value):
    """Displays the formatted coin selection lists to the console."""
    print("\n--- Coin Seçim Listeleri ---")
    
    # Determine the starting number for lists based on CMC data presence
    # and how many items are in each list for display purposes.
    cmc_list_count = len(top_market_cap) if top_market_cap else 0
    volume_list_count = len(top_volume) if top_volume else 0
    gainers_list_count = len(top_gainers) if top_gainers else 0
    decliners_list_count = len(top_decliners) if top_decliners else 0

    current_list_num = 1

    if top_market_cap:
        print(f"\n🥇 {current_list_num}. Piyasa Değerine Göre Top {cmc_list_count} Coin (CoinMarketCap Verileri):")
        print(f"  {'No.':<4} {'Sembol':<15} {'Market Cap (USD)':<20} {'Fiyat (USD)':<15} {'24s Değişim':<12}")
        for i, coin in enumerate(top_market_cap):
            market_cap_str = f"{coin['market_cap']/1_000_000_000:.2f}B" if coin['market_cap'] else "N/A"
            price_str = f"{coin['lastPrice']:.4f}" if coin['lastPrice'] else "N/A"
            change_str = f"{coin['priceChangePercent']:.2f}%" if coin['priceChangePercent'] is not None else "N/A"
            print(f"  {i+1:<3d}. {coin['symbol']:<15} {market_cap_str:<20} {price_str:<15} {change_str:<12}")
        current_list_num += 1
    else:
        logging.warning("\n🥇 Piyasa Değerine Göre Coin Listesi alınamadı veya oluşturulamadı.")

    if top_volume:
        # Original code used '2a' for volume and '2b' for gainers if CMC was present.
        # We will simplify to sequential numbering.
        print(f"\n📈 {current_list_num}. Günlük Top {volume_list_count} Hacimli Coinler (Binance):")
        print(f"  {'No.':<4} {'Sembol':<15} {'Fiyat (USDT)':<15} {'24s Değişim':<12} {'24s Hacim (USDT)':<20}")
        for i, coin in enumerate(top_volume):
            price_str = f"{coin['lastPrice']:.4f}" if coin['lastPrice'] else "N/A"
            change_str = f"{coin['priceChangePercent']:.2f}%" if coin['priceChangePercent'] is not None else "N/A"
            volume_str = f"{coin['quoteVolume']/1_000_000:.2f}M" if coin['quoteVolume'] else "N/A"
            print(f"  {i+1:<3d}. {coin['symbol']:<15} {price_str:<15} {change_str:<12} {volume_str:<20}")
        current_list_num +=1

    if top_gainers:
        print(f"\n🚀 {current_list_num}. Günlük Top {gainers_list_count} Yükselen Coinler (Binance):")
        print(f"  {'No.':<4} {'Sembol':<15} {'Fiyat (USDT)':<15} {'24s Değişim':<12} {'24s Hacim (USDT)':<20}")
        for i, coin in enumerate(top_gainers):
            price_str = f"{coin['lastPrice']:.4f}" if coin['lastPrice'] else "N/A"
            change_str = f"{coin['priceChangePercent']:.2f}%" if coin['priceChangePercent'] is not None else "N/A"
            volume_str = f"{coin['quoteVolume']/1_000_000:.2f}M" if coin['quoteVolume'] else "N/A"
            print(f"  {i+1:<3d}. {coin['symbol']:<15} {price_str:<15} {change_str:<12} {volume_str:<20}")
        current_list_num +=1

    if top_decliners:
        print(f"\n📉 {current_list_num}. Günlük Top {decliners_list_count} Düşen Coinler (Binance):")
        print(f"  {'No.':<4} {'Sembol':<15} {'Fiyat (USDT)':<15} {'24s Değişim':<12} {'24s Hacim (USDT)':<20}")
        for i, coin in enumerate(top_decliners):
            price_str = f"{coin['lastPrice']:.4f}" if coin['lastPrice'] else "N/A"
            change_str = f"{coin['priceChangePercent']:.2f}%" if coin['priceChangePercent'] is not None else "N/A"
            volume_str = f"{coin['quoteVolume']/1_000_000:.2f}M" if coin['quoteVolume'] else "N/A"
            print(f"  {i+1:<3d}. {coin['symbol']:<15} {price_str:<15} {change_str:<12} {volume_str:<20}")

def get_and_validate_user_coin_choice(all_binance_usdt_symbols, cmc_symbols_list_of_dicts):
    """Gets coin selection from user, validates it, and returns the symbol for analysis (e.g., BTCUSDT)."""
    # all_binance_usdt_symbols should be a set of strings like {'BTCUSDT', 'ETHUSDT'}
    # cmc_symbols_list_of_dicts is a list of dicts, e.g., [{'symbol': 'BTC', ...}, ...]

    while True:
        selected_symbol_input = input("\n👉 Analiz etmek istediğiniz coinin sembolünü girin (örn: BTC veya BTCUSDT) veya çıkmak için 'q' yazın: ").upper()

        if selected_symbol_input == 'Q':
            logging.info("Programdan çıkılıyor.")
            return None

        selected_symbol_for_analysis = ""
        
        # Case 1: User types 'BTC' -> we check for 'BTCUSDT' in Binance list
        # and also ensure it's not already a full CMC symbol that happens to not have USDT (e.g. a stock symbol if CMC provided it)
        if not selected_symbol_input.endswith("USDT") and (selected_symbol_input + "USDT") in all_binance_usdt_symbols:
            selected_symbol_for_analysis = selected_symbol_input + "USDT"
        # Case 2: User types 'BTCUSDT' -> we check for 'BTCUSDT' in Binance list
        elif selected_symbol_input.endswith("USDT") and selected_symbol_input in all_binance_usdt_symbols:
            selected_symbol_for_analysis = selected_symbol_input
        # Case 3: User types a CMC symbol like 'BTC' (which is in cmc_symbols_list_of_dicts's 'symbol' keys)
        # and ensure that this CMC symbol + USDT exists in the Binance list.
        elif cmc_symbols_list_of_dicts and selected_symbol_input in (c['symbol'] for c in cmc_symbols_list_of_dicts) and (selected_symbol_input + "USDT") in all_binance_usdt_symbols:
            selected_symbol_for_analysis = selected_symbol_input + "USDT"
        
        if selected_symbol_for_analysis:
            logging.info(f"Seçilen coin: {selected_symbol_input} -> Analiz edilecek: {selected_symbol_for_analysis}.")
            return selected_symbol_for_analysis
        else:
            logging.warning(f"Geçersiz veya Binance'te USDT çifti olarak bulunamayan sembol girdiniz: {selected_symbol_input}. Lütfen listelerden geçerli bir sembol girin veya 'q' ile çıkın.") 