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
script_name = 'mystock'
output_csv_file = script_name + '.csv'  # file for saving csv data
output_txt_file = script_name + '.txt'  # file for saving text data
# file containing ticker symbols, one per line.
ticker_file = 'tickers-mystock.txt'
print(
    'This script reads tickers from ',
    ticker_file,
    ' and collects relevant data.')
print('It scores by float, RSI, P/E, P/S, price change, market cap, and relative volume.')
print('')
print('** THIS SCRIPT DOES NOT ADVISE YOU WHEN TO BUY OR SELL ANYTHING **')
print('** DO YOUR OWN DUE DILIGENCE BEFORE TAKING ANY POSITIONS **')
print('')
pd.set_option('display.max_columns', 200)
pd.set_option('precision', 5)


def getuseragent():
    max_tries = 3
    for n in range(max_tries):
        try:
            u = UserAgent().random
        except Exception as e:
            print('Problem getting a UserAgent', e)
            u = []
    return u


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


with open(ticker_file, 'r') as infile:
    stock_list = infile.read().splitlines()
    stock_list = sorted(list(set(stock_list)))


# get a useragent for this session
ua = getuseragent()

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
