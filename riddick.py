import requests
import os
import re
import time
from slugify import slugify
from multiprocessing import Process, Pool
from progressbar import AnimatedMarker, Bar, BouncingBar, Counter, ETA, FileTransferSpeed, FormatLabel, Percentage, ProgressBar

# API Options
endpoint = "http://www.canneslionsarchive.com/api/winners"
headers = {
	'Authorization':'Basic czd2cURxa2NIN1RvKkQ4NEg5X0FGdURURnc5SWFmLUFvOXlD',
	'Content-Type': 'application/json',
	'User-Agent': 'Riddick v0.1'
}

session = requests.Session()

# Award options
year = 2016
collapse_subcategories = True
ignore_shortlists = True
festivals = [('CL', 'cannes-lions'), ('LI', 'lions-innovation'), ('LH', 'lions-health'), ('LE', 'lions-entertainment')]

# Local options
downloads = 'downloads'

def createDirectory(dir):
	if not os.path.exists(dir):
		os.makedirs(dir)

def save_video(url, directory, filename, extension):
	path = os.path.join(directory, "%s.%s" % (filename, extension))
	temp = "%s.tmp" % path

	# Temp file already exists, so we'll bin it and try again
	if os.path.exists(temp):
		os.remove(temp)
		os.remove(path)

	if not os.path.exists(path):
		response = session.get(url, stream=True)
		with open(temp, 'w') as f:
			f.write('\n')

		with open(path, 'wb') as f:
			total_length = int(response.headers.get('Content-Length'))
			widgets = ['Saving %s: ' % path, Percentage(), ' ', Bar(), ' ', ETA(), ' ', FileTransferSpeed()]
			pbar = ProgressBar(widgets=widgets, maxval=total_length).start()
			bytes_downloaded = 0
			for chunk in response.iter_content(chunk_size=1024):
				if chunk: # filter out keep-alive new chunks
					f.write(chunk)
					f.flush()
					bytes_downloaded += len(chunk)
					pbar.update(bytes_downloaded)
			pbar.finish()

		# Delete temp file
		os.remove(temp)

def pillage_festival(festival):
	festivalCode, slug = festival
	querystring = { 'festivalCode': festivalCode, 'year': year }

	response = requests.get("%s/categories" % endpoint, headers=headers, params=querystring)
	json = response.json()

	for index, category in enumerate(json):
		json[index]['festival'] = festivalCode
		json[index]['festivalSlug'] = slug

	pool = Pool(processes=len(json))
	pool.map_async(pillage_categories, json).get(9999999)

def pillage_categories(cat):
	category = cat['name']
	category_slug = cat['urlSlug']
	festival_slug = cat['festivalSlug']
	festival = cat['festival']
	timestamp = int(round(time.time() * 1000))

	post_data = {
		'type':'winners',
		'timeStamp': timestamp,
		'pageIndex':1,
		'sortType':0,
		'resultsPerPage':1500,
		'isDetailSearch':False,
		'fields':'null',
		'criteria': {
			'festivalUrlSlug': festival_slug,
			'festivalCode': festival,
			'category': category_slug,
			'year': year,
			'selectedPrizeFilters':[],
			'selectedSection': None,
			'selectedSubCategory': None
		}
	}

	response = requests.post(endpoint, headers=headers, json=post_data)
	json = response.json()
	winners = 0
	mc_results = json['results']['mediaCategoryResults']
	for mc_result in mc_results:
		c_results = mc_result['categoryResults']
		for c_result in c_results:
			results = c_result['results']
			for result in results:
				prizes = result['prizes']
				if 'mainMedia' in result:
					main_media = result['mainMedia']
					for prize in prizes:
						if (ignore_shortlists is False) or (ignore_shortlists is True and prize['description'] != 'Shortlist'):
							subcategory = slugify(mc_result['name'])
							result_subcategory = slugify(c_result['name'])
							prize_description = slugify(prize['description'])
							directory = os.path.join(downloads, str(year), festival_slug, category_slug, subcategory, result_subcategory, prize_description)
							media_url = main_media['mediaUri']
							filename = result['friendlyName']
							extension = main_media['extension']

							if category_slug == subcategory:
								directory = os.path.join(downloads, str(year), festival_slug, category_slug, result_subcategory, prize_description)
								if category_slug == result_subcategory:
									directory = os.path.join(downloads, str(year), festival_slug, category_slug, prize_description)

							if collapse_subcategories is True:
								directory = os.path.join(downloads, str(year), festival_slug, category_slug, prize_description)

							# Create the directory
							createDirectory(directory)

							# Save video
							save_video(media_url, directory, filename, extension)

							# Keep track of winners
							winners = winners +1

	print "%d winners in %s" % (winners, category)

def main():
	for festival in festivals:
		print "----------------------------------"
		print "Pillaging %s" % festival[1]
		print "----------------------------------"
		pillage_festival(festival)

main()
