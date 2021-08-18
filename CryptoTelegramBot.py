import os
# import memory_profiler
import telepot
import urllib.request
import json
import io
from datetime import datetime
import matplotlib.pyplot as plt
from telepot.loop import MessageLoop
import time
import gc
from PIL import Image
import math
from TelegramAPI import TELEGRAM_BOT_API


HELP_TEXT = {"!p [coin_name / 'all']": "Gets graphs for a given coin",
             "!a [min / max] [coin_name] [amount]": "Adds an alert for a given coin",
             "!a 'list'": "Lists all alerts"}
SHORT_CRYPTO_NAMES = {"e": "ethereum", "m": "monero", "p": "polkadot", "t": "tron"}
MIN_ALERT_FILE = "min_alerts.json"
MAX_ALERT_FILE = "max_alerts.json"


# def create_ticks(all_coords, round_to):
#     # Create ticks
#     ticks = []
#     min_value = min(all_coords)
#     max_value = max(all_coords)
#     for i in range(math.floor(min_value / round_to) * round_to, math.ceil(max_value / round_to + 1) * round_to, round_to):
#         ticks.append(i)
#     return ticks


class CryptoTelegramBot:
    def __init__(self):
        if not os.path.exists(MIN_ALERT_FILE):
            with open(MIN_ALERT_FILE, "w", encoding="utf-8") as file:
                json.dump({}, file)
        with open(MIN_ALERT_FILE, "r", encoding="utf-8") as file:
            self.__min_alerts = json.load(file)
        if not os.path.exists(MAX_ALERT_FILE):
            with open(MAX_ALERT_FILE, "w", encoding="utf-8") as file:
                json.dump({}, file)
        with open(MAX_ALERT_FILE, "r", encoding="utf-8") as file:
            self.__max_alerts = json.load(file)
        self.__bot = telepot.Bot(TELEGRAM_BOT_API)
        print(self.__bot.getMe())
        self.__valid_crypto_names = self.get_valid_names()
        # Start listening to the telegram bot and whenever a message is  received, the handle function will be called.
        MessageLoop(self.__bot, self.handle_message).run_as_thread()
        print('Listening....')
        self.handle_alerts()
        # while 1:
        #     time.sleep(900)

    def get_valid_names(self):
        """
        Fetches valid crypto_names
        :return: dict
        """
        url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
        try:
            with urllib.request.urlopen(url) as site:
                temp_data = json.loads(site.read())
            ids = []
            for value in temp_data:
                ids.append(value.get("id"))
        # Backup
        except:
            with open("valid_names.txt", "r", encoding="utf-8") as file:
                ids = file.readline().split(", ")
        ids = set(ids)
        return ids

    def make_graph(self, title, data):
        """
        Crafts a graph
        :param title: str
        :param data: dict
        :return: Plot figure
        """
        given_fig, given_plot = plt.subplots(num=title)
        # Timestamps are in milliseconds
        date_objects = [datetime.fromtimestamp(timestamp / 1000) for timestamp in data.keys()]
        given_plot.plot(date_objects, data.values())

        given_plot.grid()
        # y_ticks = create_ticks(data.values(), 1000)
        # x_ticks = create_ticks(data.keys(), 1000)
        # given_plot.set_yticks(y_ticks)
        # given_plot.set_xticks(x_ticks)
        given_plot.set_title(title)
        given_plot.set_xlabel("Time")
        given_plot.set_ylabel("Price (€)")
        given_fig.set_figwidth(10)
        given_fig.set_figheight(6)
        return given_fig

    def get_historical_data(self, crypto_name):
        """
        Gets prices
        :param crypto_name: str
        :return: list, List of plot figure
        """
        # https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=eur&days=max
        base_url = f"https://api.coingecko.com/api/v3/coins/{crypto_name}/market_chart?vs_currency=eur"
        time_frames = [90, 7, 1]
        graphs = []
        for time_frame in time_frames:
            url = f"{base_url}&days={time_frame}"
            try:
                with urllib.request.urlopen(url) as site:
                    temp_data = json.loads(site.read()).get("prices")
                    data = {}
                    for pair in temp_data:
                        timestamp = pair[0]
                        price = pair[1]
                        data[timestamp] = price
                    title = f"{crypto_name.capitalize()} ({time_frame} days)"
                    graphs.append(self.make_graph(title, data))
            except:
                print("ERROR")
        return graphs

    def combine_vertically(self, images):
        """
        Combines images to one image vertically
        :param images: list
        :return: Image
        """
        widths, heights = zip(*(i.size for i in images))
        total_width = max(widths)
        max_height = sum(heights)
        new_im = Image.new('RGB', (total_width, max_height))
        y_offset = 0
        for im in images:
            new_im.paste(im, (0, y_offset))
            y_offset += im.size[1]
        return new_im

    def combine_horizontally(self, images):
        """
        Combines images to one image horizontally
        :param images: list
        :return: Image
        """
        widths, heights = zip(*(i.size for i in images))
        total_width = sum(widths)
        max_height = max(heights)
        new_im = Image.new('RGB', (total_width, max_height))
        x_offset = 0
        for im in images:
            new_im.paste(im, (x_offset, 0))
            x_offset += im.size[0]
        return new_im

    # @memory_profiler.profile()
    def get_images(self, crypto_name):
        """
        Makes images for a given crypto
        :param crypto_name: str
        :return: Image
        """
        graphs = self.get_historical_data(crypto_name)
        images_bytes = []
        for i, graph in enumerate(graphs):
            buf = io.BytesIO()
            graph.savefig(buf, format="png", bbox_inches='tight')
            buf.seek(0)
            images_bytes.append(buf.getvalue())
            # Send images separately by uncommenting line below
            # bot.sendPhoto(chat_id, buf)
        # bot.sendMediaGroup(chat_id, images)
        images = [Image.open(io.BytesIO(image_data)) for image_data in images_bytes]
        new_im = self.combine_vertically(images)
        # Clear the current axes.
        plt.cla()
        # Clear the current figure.
        plt.clf()
        # Closes all the figure windows.
        plt.close('all')
        gc.collect()
        return new_im

    def get_crypto_name(self, crypto_name):
        """
        Gets a crypto name from string
        :param crypto_name: str
        :return: str
        """
        if crypto_name in SHORT_CRYPTO_NAMES:
            crypto_name = SHORT_CRYPTO_NAMES.get(crypto_name)
        elif crypto_name not in self.__valid_crypto_names:
            return None
        return crypto_name

    def price_command(self, chat_id, commands):
        """
        Handles !price command
        :param chat_id:
        :param commands: list
        :return: nothing
        """
        crypto_name = commands[1].lower()
        images = []
        if crypto_name == "all":
            self.__bot.sendMessage(chat_id, f"Fetching all favourites.")
            for crypto_name in SHORT_CRYPTO_NAMES.values():
                images.append(self.get_images(crypto_name))
        else:
            crypto_name = self.get_crypto_name(crypto_name)
            if crypto_name is not None:
                self.__bot.sendMessage(chat_id, f"Fetching {crypto_name.capitalize()}.")
                images.append(self.get_images(crypto_name))
            else:
                self.__bot.sendMessage(chat_id, "Not a valid cryptocurrency!")
                return
        # Uncomment line below and comment the line below it to combine all photos
        # new_im = combine_horizontally(images)
        for new_im in images:
            buf = io.BytesIO()
            new_im.save(buf, "png")
            buf.seek(0)
            self.__bot.sendPhoto(chat_id, buf)

    def write_alerts_to_disk(self):
        """
        Writes alerts to disk
        :return: nothing
        """
        with open(MIN_ALERT_FILE, "w", encoding="utf-8") as file:
            json.dump(self.__min_alerts, file)
        with open(MAX_ALERT_FILE, "w", encoding="utf-8") as file:
            json.dump(self.__max_alerts, file)

    def alert_command(self, chat_id, commands):
        """
        Handles !alert command
        :param chat_id:
        :param commands: list
        :return: nothing
        """
        chat_id = str(chat_id)
        command = commands[1]
        if command == "list":
            message = ""
            for coin_id in self.__min_alerts.get(chat_id):
                message += f"{coin_id.capitalize()}: <{self.__min_alerts.get(chat_id).get(coin_id)} €\n"
            for coin_id in self.__max_alerts.get(chat_id):
                message += f"{coin_id.capitalize()}: >{self.__max_alerts.get(chat_id).get(coin_id)} €\n"
            self.__bot.sendMessage(chat_id, message)
            return
        crypto_name = commands[2].lower()
        amount = float(commands[3])
        crypto_name = self.get_crypto_name(crypto_name)
        if crypto_name is None:
            self.__bot.sendMessage(chat_id, "Not a valid cryptocurrency!")
            return
        if command == "min":
            self.__min_alerts[chat_id][crypto_name] = amount
            self.__bot.sendMessage(chat_id, f"Added alert for {crypto_name.capitalize()} at <{amount} €")
            # Add empty dictionary to max_alerts to not cause error on handle_alerts
            if chat_id not in self.__max_alerts:
                self.__max_alerts[chat_id] = {}
            self.write_alerts_to_disk()
        elif command == "max":
            self.__max_alerts[chat_id][crypto_name] = amount
            self.__bot.sendMessage(chat_id, f"Added alert for {crypto_name.capitalize()} at >{amount} €")
            # Add empty dictionary to min_alerts to not cause error on handle_alerts
            if chat_id not in self.__min_alerts:
                self.__max_alerts[chat_id] = {}
            self.write_alerts_to_disk()

    def handle_alerts(self):
        """
        Handles alerts
        :return: nothing
        """

        def get_data(coin_id):
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            try:
                with urllib.request.urlopen(url) as site:
                    current_price = json.loads(site.read()).get("market_data").get("current_price").get("eur")
                    return current_price
            except:
                print("ERROR IN ALERTS")
                return None

        while True:
            error = False
            message = ""
            for chat_id in set(self.__min_alerts.keys()).union(set(self.__max_alerts.keys())):
                chat_id = str(chat_id)
                for coin_id in set(self.__min_alerts.get(chat_id).keys()).union(set(self.__max_alerts.get(chat_id).keys())):
                    current_price = get_data(coin_id)
                    if current_price is None:
                        error = True
                        continue
                    # Check min alerts
                    if coin_id in self.__min_alerts.get(chat_id):
                        if current_price <= self.__min_alerts.get(chat_id).get(coin_id):
                            message += f"{coin_id.capitalize()} is currently at {current_price} € " \
                                       f"(<{self.__min_alerts.get(chat_id).get(coin_id)} €)\n"
                            self.__min_alerts.get(chat_id).pop(coin_id, None)
                            self.write_alerts_to_disk()
                    # Check max alert
                    if coin_id in self.__max_alerts.get(chat_id):
                        if current_price >= self.__max_alerts.get(chat_id).get(coin_id):
                            message += f"{coin_id.capitalize()} is currently at {current_price} € " \
                                       f"(>{self.__max_alerts.get(chat_id).get(coin_id)} €)\n"
                            self.__max_alerts.get(chat_id).pop(coin_id, None)
                            self.write_alerts_to_disk()
                if error:
                    self.__bot.sendMessage(chat_id, "Error while fetching current price!")
                if message != "":
                    self.__bot.sendMessage(chat_id, message)
            time.sleep(900)

    def help_command(self, chat_id, commands):
        """
        Handles !help command
        :param chat_id:
        :param commands: list
        :return: nothing
        """
        message = ""
        for command in HELP_TEXT:
            message += f"{command}: {HELP_TEXT.get(command)}\n"
        self.__bot.sendMessage(chat_id, message)

    def handle_message(self, message):
        print("Message received!")
        chat_id = message.get("chat").get("id")
        message_text = message.get("text")
        commands = message_text.split()
        command = commands[0]
        if command == "!p":
            self.price_command(chat_id, commands)
        elif command == "!a":
            self.alert_command(chat_id, commands)
        elif command == "!h":
            self.help_command(chat_id, commands)


def main():
    plt.switch_backend('agg')
    CryptoTelegramBot()


if __name__ == "__main__":
    main()
