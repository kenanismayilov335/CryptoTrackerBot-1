# CryptoTrackerBot
A Telegram bot for tracking crypto currency prices

## Installation
1. Install **Python 3** (minimum Python **3.8**) and **Pip**.
2. Install dependencies:
```sh
pip install -r requirements.txt
```
3. Get telegram bot token
4. Add telegram bot token to **TelegramAPI.py**
5. Run **CryptoTelegramBot.py**

## Usage
- Help:
```
!h
```
- Get graphs for a given currency or all currencies:
```
!p <currency>
!p all
```
- Add alerts for a given currency:
```
!a min <currency> <amount>
!a max <currency> <amount>
```
- List all alerts:
```
!a list
```
