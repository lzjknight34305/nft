# Term definition - 
#   Floor - The minimum price of most recently N traded assets.
#   Believer rate - # of asset not on sale / # of total assets.

import requests
import datetime
import time


ASSETS_API = "https://api.opensea.io/api/v1/assets"
FLOOR_AVERAGE = 5

class Asset:
    # All timestamps are in UTC with the precision of second.
    def __init__(self, contract_address, token_id, last_trade_timestamp, trade_price, on_sale, sale_create_timestamp):
        self.contract_address = contract_address
        self.token_id = token_id
        
        self.last_trade_timestamp = last_trade_timestamp
        self.trade_price = trade_price
        self.on_sale = on_sale
        self.sale_create_timestamp = sale_create_timestamp

    
    def __lt__(self, other):
         return self.trade_price < other.trade_price


class Collection:
    # All assets will be fetched in reverse-chron order by trading day.
    # We will get the maximum number assets when cap is specified, 
    # otherwise we will try to fetch all.
    def __init__(self, collection_name, cap=None):
        self.cap = cap
        self.collection_name = collection_name        
        self.assets = self._fetch()

    def get_floor_price(self, time_window_hour = 24):
        cutoff_timestamp = int(time.time()) - time_window_hour * 3600
        assets = []
        for asset in self.assets:
            if asset.last_trade_timestamp is None:
                continue
            if asset.last_trade_timestamp > cutoff_timestamp:
                assets.append(asset)

        assets.sort()
        floor_price = None

        total = 0.0
        counter = 0

        for asset in assets:
            if asset.trade_price is None:
                continue
            total += asset.trade_price
            counter += 1
            if counter == FLOOR_AVERAGE:
                break
        if counter > 0:
            floor_price = total / counter
        return floor_price
    
    def get_believer_ratio(self):
        total_asset_count = len(self.assets)
        believer_count = 0
        for asset in self.assets:
            if asset.on_sale is False:
                believer_count += 1
        return float(believer_count) * 100.0 / float(total_asset_count)


    def _fetch(self):
        print("LOG: Fething assets from collection: ", self.collection_name)
        assets = []
        query = {"order_by":"sale_date","order_direction":"desc","offset":"50","limit":"50","collection":self.collection_name}
        offset = 0
        while True:
            # time.sleep(0.1)
            print("LOG: Fetching ", offset, "...")
            query["offset"] = str(offset)
            offset += int(query["limit"])
            response = requests.request("GET", ASSETS_API, params=query)
            json_assets = response.json()['assets']
            if len(json_assets) == 0:
                break
            for json_asset in json_assets:
                assets.append(self._parse_asset(json_asset))
            if self.cap is not None and len(assets) >= self.cap:
                break
        return assets

    def _parse_asset(self, json_asset):
        last_trade_timestamp, trade_price = None, None
        on_sale, sale_create_timestamp = False, None
        if json_asset["last_sale"]:
            trade_price = float(json_asset["last_sale"]["total_price"]) / 1e18
            last_trade_time = datetime.datetime.fromisoformat(json_asset["last_sale"]["event_timestamp"])
            last_trade_timestamp = last_trade_time.timestamp()
        if json_asset["sell_orders"] and len(json_asset["sell_orders"]) > 0 and not json_asset["sell_orders"][0]["created_date"]:
            on_sale = True
            sale_create_time = datetime.datetime.fromisoformat(json_asset["sell_orders"][0]["closing_date"])
            sale_create_timestamp = sale_create_time.timestamp()

        contract_address = json_asset["asset_contract"]["address"]
        token_id = json_asset["token_id"] 

        return Asset(contract_address, token_id, last_trade_timestamp, trade_price, on_sale, sale_create_timestamp)



meebits = Collection("meebits", 2000)

# Get the floor price in last day.
print("The floor price of meebits in last hour is: ", meebits.get_floor_price(1))

# Get the total believer ratio.
# Ongoing feature.
# print("The overall believer rate of meebits is: ", meebits.get_believer_ratio())