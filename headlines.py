#!/usr/bin/env python3

from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing.dummy import Lock as ThreadLock
from multiprocessing import cpu_count as CPUcount
from time import sleep
import requests
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import html5lib
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
print('This script collects news headlines and measures sentiment.')
print('')
print('** THIS SCRIPT DOES NOT ADVISE YOU WHEN TO BUY OR SELL ANYTHING **')
print('** DO YOUR OWN DUE DILIGENCE BEFORE TAKING ANY POSITIONS **')
print('')
print('')


one_cpu = CPUcount()
two_cpu = 2 * one_cpu
global max_tries
max_tries = 3
news_tables = {}
parsed_data = []
ticker_file = 'tickers-mystock.txt'


def getuseragent():
    for n in range(max_tries):
        try:
            u = UserAgent().random
        except Exception as e:
            print('Problem getting a UserAgent', e)
            u = []
        return u


def random_wait():
    # randomize a waiting period
    wait_times = [
        0.7,
        0.8,
        0.9,
        1,
        1.1,
        1.2,
        1.3,
        1.4,
        1.5,
        1.6,
        1.7,
        1.8,
        1.9,
        2.0,
        2.1,
        2.2]
    choice = np.random.choice(wait_times)
    return choice


def get_url_data(url):
    headers = {'User-Agent': getuseragent()}
    for n in range(max_tries):
        sleep(random_wait())
        try:
            return requests.Session().get(url, headers=headers, timeout=30)
        except requests.exceptions.RequestException as e:
            print(e)
            print('Retrying after 30 seconds...')
            if n == max_tries - 1:
                exit
                sleep(30)
        except requests.exceptions.ConnectionError as e:
            print('Retrying after 30 seconds...')
            if n == max_tries - 1:
                exit
                sleep(30)
        except requests.exceptions.ChunkedEncodingError as e:
            print('Retrying after 30 seconds...')
            if n == max_tries - 1:
                exit
                sleep(30)


def get_headline_data(tickers):
    global news_table
    print('Getting data, please stand by...')

    def pull_url(ticker, lock):
        try:
            url = ('http://finviz.com/quote.ashx?t=' + ticker.lower())
            req = get_url_data(url).content
            html = BeautifulSoup(req, 'html5lib')
            with lock:
                news_table = html.find(id='news-table')
                news_tables[ticker] = news_table
                print('Found data for', ticker)
        except Exception as e:
            print(ticker, 'Ticker symbol data incomplete.', e)
        return news_table
    if __name__ == "__main__":
        pool = ThreadPool(two_cpu)
        lock = ThreadLock()
        for ticker in tickers:
            pool.apply_async(pull_url, args=(ticker, lock, ))
        pool.close()
        pool.join()


with open(ticker_file, 'r') as infile:
    tickers = infile.read().splitlines()
    tickers = sorted(list(set(tickers)))


# get a useragent for this session
ua = getuseragent()

# get a table of tables of headlines
get_headline_data(tickers)

for ticker, news_table in news_tables.items():
    for row in news_table.findAll('tr'):
        title = row.a.text
        date_data = row.td.text.split(' ')

        if len(date_data) == 1:
            time = date_data[0]
        else:
            date = date_data[0]
            time = date_data[1]

        parsed_data.append([ticker, date, time, title])

df = pd.DataFrame(parsed_data, columns=['ticker', 'date', 'time', 'title'])
df
vader = SentimentIntensityAnalyzer()


def f(title): return vader.polarity_scores(title)['compound']


df['compound'] = df['title'].apply(f)
df['date'] = pd.to_datetime(df.date).dt.date

plt.figure(figsize=(10, 8))
mean_df = df.groupby(['ticker', 'date']).mean().unstack()
mean_df = mean_df.xs('compound', axis="columns")
mean_df.plot(kind='bar')
plt.show()
