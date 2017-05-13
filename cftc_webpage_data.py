import csv
from pymongo import MongoClient
import pandas as pd
import re
from bs4 import BeautifulSoup
import requests
import json
from datetime import datetime


# URL of webpage to extract data 
cftc_webpage = "http://www.cftc.gov/dea/newcot/FinComWk.txt"
header_page = requests.get("http://www.cftc.gov/MarketReports/" \
							"CommitmentsofTraders/HistoricalViewable/cotvariablestfm")
initial_data = "/Users/GW/Documents/trading_platform/"

#Establish the MongoDB Connection
client = MongoClient()
db = client.cftc


def get_headers():
	'''
	This fucntion uses the BeautifulSoup library to scrape the CFTC website for a list of 
	headers to the COT Financial Futures data. 

	The only input is the header_page variable defined at the beginning of the code

	'''
	
	headers = []
	soup = BeautifulSoup(header_page.text, 'lxml')

	section = soup.find(id="box-text_image")
	list_box = section.find_all('p')
	for lb in list_box:
		if re.search(r'^[0-9]', lb.text):
			text_name = re.sub(r'^([0-8][0-9]|[0-9])\ *', '', lb.text).rstrip()
			headers.append(text_name.encode('utf-8'))

	return headers

def compile_data(file, need_header):
	'''
	This function will read a csv file into Python, clean the data, and export it into 
	a MongoDB database. 

	Function inputs:
		file -> the csv file to import data from
		need_header -> a True/False operator to determine if the list of headers also needs
						to be imported

	'''

	# Determine if a list of headers are needed to append to the data import
	if need_header:
		head_index = None
		df_head = pd.DataFrame(data=get_headers()).T
	else:
		head_index = 0
		
	# Read contents of webpage into a pandas dataframe
	df = pd.read_csv(file, header=head_index, low_memory=False)

	#Check the Report_Date column for dtype
	df.iloc[:,2] = pd.to_datetime(df.iloc[:,2], 
		infer_datetime_format=True, box=False)
	df.iloc[:,2] = df.iloc[:,2].dt.strftime("%Y-%m-%d")

	# Combine the headers with the new data
	if need_header:	
		frames = [df_head, df]
		df = pd.concat(frames, ignore_index=True)
		
		# Move first row to become the header	
		df.columns = df.loc[0,:]
		df.drop(df.index[0], inplace=True)

	df.rename(columns={'Report_Date_as_YYYY-MM-DD': 'Report_Date_as_YYYY_MM_DD', 
					   'Report_Date_as_MM_DD_YYYY': 'Report_Date_as_YYYY_MM_DD'},
						inplace=True)

	# Replace values that only contain a decimal "."
	df.replace(to_replace="\A\.", value=0, regex=True, inplace=True)

	# Create a ditionary from the array
	df2 = df.to_dict(orient='records')

	# Insert new files into DB
	db.cot_financial.insert_many(df2)


if __name__ == "__main__":
	# Various files to process and load into database

	# Use to import historical data prior to this year. Uncomment if not imported yet
	#compile_data(initial_data + 'C_TFF_2006_2016.csv', False) 
	
	# Use to import this year's data. Uncomment if not imported yet
	#compile_data(initial_data + 'FinComYY.txt', False)

	# Use to import the most recent release directly from the CFTC website
	compile_data(cftc_webpage, True)
