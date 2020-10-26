#!/usr/bin/env python3

import datetime
import math
import threading
from time import sleep

import html5lib
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

stime = datetime.datetime.now()
script_name = 'lowfloats'
output_csv_file = script_name + '.csv'  # file for saving csv data
output_txt_file = script_name + '.txt'  # file for saving text data
output_ticker_file = 'tickers-scanned.txt'  # file for saving new tickers
print('This script compiles a list of tickers of low float,')
print('young companies, with relative volume between 1 and 2.')
print('')
print('** THIS SCRIPT DOES NOT ADVISE YOU WHEN TO BUY OR SELL ANYTHING **')
print('** DO YOUR OWN DUE DILIGENCE BEFORE TAKING ANY POSITIONS **')
print('')
pd.set_option('display.max_columns', 200)
pd.set_option('precision', 5)

# Get a group of tickers of young, low float companies with relative
# volume above 1
urls_a = ['https://finviz.com/screener.ashx?v=141&f=cap_smallunder,geo_usa,ipodate_prev2yrs,sh_float_u20,sh_outstanding_u20,sh_relvol_o1&ft=4&o=-relativevolume']

# Get another group of tickers of young, low float companies with relative
# volume below 2
urls_b = ['https://finviz.com/screener.ashx?v=141&f=cap_smallunder,geo_usa,ipodate_prev2yrs,sh_float_u20,sh_outstanding_u20,sh_relvol_u2&ft=4&o=-relativevolume']


def getuseragent():
    max_tries = 3
    for n in range(max_tries):
        try:
            u = UserAgent().random
            return u
        except Exception as e:
            print('Problem getting a UserAgent', e)


def cleanupdata(var):
    var = str(var).replace('%', '')
    var = str(var).replace(',', '')
    var = str(var).replace('k', 'e3')
    var = str(var).replace('M', 'e6')
    var = str(var).replace('B', 'e9')
    var = str(var).replace('T', 'e12')
    var = float(var)
    return var


def fundamental_metric(soup, m):
    if m != 'Score' and m != 'Rotation':
        var = soup.find(text=m).find_next(class_='snapshot-td2').text
        var = cleanupdata(var)
    if m == 'Score' or m == 'Rotation':
        var = 0
    return var


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
    max_tries = 10
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
        except requests.exceptions.ChunkedEncodingError as e:
            print('Retrying after 30 seconds...')
            if n == max_tries - 1:
                exit
            sleep(30)
        except requests.exceptions.ConnectionError as e:
            print('Retrying after 30 seconds...')
            if n == max_tries - 1:
                exit
            sleep(30)


def get_tickers(urls_a, urls_b):
    q = []
    r = []
    n = []

    def harvest_finviz_links(url):
        html = get_url_data(url).content
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup.find_all('a', class_='screener-link-primary'):
            r.append(tag.text)

    if __name__ == "__main__":
        minhits = 1
        threads1 = [
            threading.Thread(
                target=harvest_finviz_links,
                args=(
                    url,
                )) for url in urls_a]
        for thread in threads1:
            thread.start()
            sleep(random_wait())
        for thread in threads1:
            thread.join()
        r = sorted(list(set([x for x in r if r.count(x) > (minhits - 1)])))
        for item in r:
            q.append(item)

        r = []
        minhits = 1
        threads2 = [
            threading.Thread(
                target=harvest_finviz_links,
                args=(
                    url,
                )) for url in urls_b]
        for thread in threads2:
            thread.start()
            sleep(random_wait())
        for thread in threads2:
            thread.join()
        r = sorted(list(set([x for x in r if r.count(x) > (minhits - 1)])))
        for item in r:
            q.append(item)
        r = []
    # find elements appearing in all scans (duplicates)
    # the minimum depends on how many hits are required
    # from urls_a and urls_b (normally one from each)
    q = sorted(list(set([x for x in q if q.count(x) > 1])))
    return q


def get_fundamental_data(df):
    print('Getting data, please stand by...')
    for symbol in df.index:
        try:
            url = ('http://finviz.com/quote.ashx?t=' + symbol.lower())
            html = get_url_data(url).content
            soup = BeautifulSoup(html, 'html5lib')
            print('Retrieved data for ' + symbol)
            for m in df.columns:
                df.loc[symbol, m] = fundamental_metric(soup, m)
        except Exception as e:
            print('Data for ticker ' + symbol + ' incomplete.', e, m)
    return df


# get a useragent for this session
ua = getuseragent()

# create a list of tickers for interesting stocks
stock_list = get_tickers(urls_a, urls_b)

# create a dataframe based on tickers and pertinent variables
metric = ['Price', 'Change', 'Market Cap', 'Sales', 'Sales Q/Q', 'P/S', 'Forward P/E',
          'EPS next Y', 'Shs Float', 'RSI (14)', 'Rel Volume', 'Volume', 'Rotation',
          'Score']
df = pd.DataFrame(index=stock_list, columns=metric)

# get data and populate the dataframe
df = get_fundamental_data(df)
df.dropna(axis=0, how='any', inplace=True)

# derive more variables from raw data
# relative volume
rvol_fac = 30 / df['RSI (14)'] * (df['Change'] / df['Rel Volume'])
# float
float_fac = (df['Market Cap'] / df['Shs Float'])**0.5
# float rotation
rot_fac = (df['Volume'] / df['Shs Float']) * 10
# price per unit sales and sales growth
sales_fac = (df['Sales'] / df['Market Cap']) * (1 + df['Sales Q/Q'] / 100) * 10
# price to earnings and earnings growth
pe_fac = (df['Forward P/E'] * (1 + df['EPS next Y'] / 100)) * 10

# calculate a score and rank the stocks
score = rvol_fac + float_fac + rot_fac + sales_fac + pe_fac
df['Score'] = score
df['Rotation'] = rot_fac
df.round(5)
# temporarily disable filtering minimum score
df = df[(df[['Score']] > -1e6).all(axis=1)]
df = df.sort_values('Score', ascending=False)

# save the list of tickers
with open(output_ticker_file, "w") as ticker_file:
    ticker_file.write('\n'.join(list(df.index)))

runtime = 'Elapsed Runtime: ' + str(datetime.datetime.now() - stime)
rundate = 'Rundate: ' + str(datetime.date.today())

# present and save the data
print('')
print(
    rundate +
    ', ' +
    'Name: ' +
    script_name +
    ', ' +
    runtime +
    ', Formatted Data Frame:')
print(df)
df.to_csv(output_csv_file, float_format='%g')

with open(output_txt_file, "w") as text_file:
    text_file.write(
        '\n\n' +
        rundate +
        ', ' +
        'Name: ' +
        script_name +
        ', ' +
        runtime +
        ', Formatted Data Frame:' +
        '\n')  # write date to the file
    df.to_string(text_file)
