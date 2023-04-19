import pandas as pd
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance.enums import SIDE_SELL, TIME_IN_FORCE_GTC, ORDER_TYPE_STOP_LOSS_LIMIT, ORDER_TYPE_LIMIT, SIDE_BUY
import requests
import numpy as np
import datetime

symbol = "ETHUSDT"
interval = Client.KLINE_INTERVAL_1HOUR

start_time = datetime.datetime.now()

# Binance API endpoint üzerinden sisteme ekmek yemek için müsade istiyoruz.
exchange_info_url = "https://api.binance.com/api/v3/exchangeInfo"
exchange_info = requests.get(exchange_info_url).json()
symbol_index = next(
    (
        i
        for i, symbol in enumerate(exchange_info["symbols"])
        if symbol["symbol"] == "ETHUSDT"
    ),
    None,
)
min_notional = float(
    exchange_info["symbols"][symbol_index]["filters"][3].get("minNotional", 0)
)
tick_size = float(exchange_info["symbols"][symbol_index]["filters"][0]["tickSize"])
step_size = float(exchange_info["symbols"][symbol_index]["filters"][2].get("stepSize", 0))

server_time = requests.get("https://api.binance.com/api/v3/exchangeInfo").json()[
    "serverTime"
]
print("Server time:", server_time)

#canlarım cigerlerim aşagıdaki yere api keylerin bulunduğu konumu eklemeniz yeter ya da ben daha farklı bir yol izlicem derseniz amenna
with open("c:/Users/atina/fisildayan/kovboy/BalikesirinCilginEsekleri.txt", "r") as f:
    lines = f.readlines()
    API_KEY = lines[0].strip()
    API_SECRET = lines[1].strip()
client = Client(API_KEY, API_SECRET)
usdt_balance = client.get_asset_balance(asset="USDT")
exchange_info = client.get_exchange_info()
symbol = "ETHUSDT"
interval = Client.KLINE_INTERVAL_1HOUR


buy = False
sell = False

usdt_balance = float(usdt_balance["free"])

while True:
    try:
        symbol_info = client.get_symbol_info(symbol)
    except BinanceAPIException as e:
        print(e)
        time.sleep(60)
        continue
        
    step_size = None
    for filter in symbol_info["filters"]:
        if filter["filterType"] == "LOT_SIZE":
            if "stepSize" in filter:
                step_size = float(filter["stepSize"])

    klines = client.get_klines(symbol=symbol, interval=interval, limit=200)
    data = pd.DataFrame(
        klines,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "ignore",
        ],
    )
    data = data.astype(float)

    data["ema12"] = data["close"].ewm(span=12).mean()
    data["ema26"] = data["close"].ewm(span=26).mean()
    data["macd"] = data["ema12"] - data["ema26"]
    data["signal"] = data["macd"].ewm(span=9).mean()

    data["positions"] = np.where(data["macd"] < data["signal"], 1, 0)
    data["positions"] = np.where(data["macd"] > data["signal"], -1, data["positions"])

    if data["positions"].iloc[-1] == 1 and not buy:
        print("BUY")
        buy = True
        sell = False
        step_size = 0.001
        min_notional = 10
        usdt_balance = float(client.get_asset_balance(asset="USDT")["free"])
        quantity = usdt_balance / float(data["close"].iloc[-1])
        quantity = quantity - (quantity % step_size)
        if quantity * float(data["close"].iloc[-1]) < min_notional:
            quantity = (min_notional / float(data["close"].iloc[-1])) - (
                (min_notional / float(data["close"].iloc[-1])) % step_size
            )
        print("Quantity: ", quantity)
        try:
            order = client.create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                price=str(data["close"].iloc[-1]),
                quantity=str(quantity),
                recvWindow=10000,
            )
            print(order)
        except Exception as e:
            print(e)
    elif data["positions"].iloc[-1] == -1 and not sell:
        print("SELL")
        sell = True
        buy = False
        eth_balance = float(client.get_asset_balance(asset="ETH")["free"])
        eth_balance = eth_balance - (eth_balance % step_size)
        print("ETH Balance: ", eth_balance)
        try:
            order = client.create_order(
                symbol=symbol,
                side=SIDE_SELL,
                type=ORDER_TYPE_STOP_LOSS_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                stopPrice=str(data["close"].iloc[-1] * 0.99),
                price=str(data["close"].iloc[-1] * 0.98),
                quantity=str(eth_balance),
                recvWindow=10000,
            )
            print(order)
        except Exception as e:
            print(e)
    time.sleep(10)

# bot tıngır mıngır çalışan simetride ilerliyor. Çok keskin hatları yok ama stop loss belki daha da keskinleştirilebilir. 
# kod fena geliştirmeye müsait bi el atarsınız 
# grafik mrafik gömer, tatlış bir UI yapabilirseniz harika olur
# şimdi az kafam çok dolu AI nasıl kullanabiliriz diye bir taraftan bakacağım, gavur abilerin bir kaç
# entegrasyon macerasını izliyorum.
# botu anlatmadım bu arada, bot api key file gösterince çalışır, ve USDT bakiyesinde alabileceği
# en düşük miktar ETH ile başlar al-sat yakaladıkça oran artar. 1 saatlik dilime göre hareket eder
# Kendini katlamak üzere tasarlanmış olup altın oranı sever.
# gerekli libleri yüklemeyi zaten unutmassınız da bir not olsun. Kendinize iyi bakın.