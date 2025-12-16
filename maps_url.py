import time
from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

place = input ("Place: ")

chrome_options = Options ()
chrome_options.page_load_strategy = "none"
driver = webdriver.Chrome (options = chrome_options)

driver.get ("https://www.google.com/maps/search/?api=1&query=" + quote_plus (place))
# lat, lon = driver.page_source.split ("/staticmap?center=", 1) [1].split ("&amp;", 1) [0].split ("%2C", 1)
while "/maps/place/" not in driver.current_url:
    if "/maps/search/?api=1" not in driver.current_url and "/maps/search/" in driver.current_url:
        print ("No results found")
        raise SystemExit
    time.sleep (0.1)
place_id = driver.current_url.split ("!1s", 1) [1].split ("!", 1) [0]
lat = driver.current_url.split ("!3d", 1) [1].replace ("?", "!", 1).split ("!", 1) [0]
lon = driver.current_url.split ("!4d", 1) [1].replace ("?", "!", 1).split ("!", 1) [0]
print (f"URL: https://www.google.com/maps/preview/place/@{lat},{lon},2570a,13.1y/data=!4m2!3m1!1s{place_id}")
print (f"Latitude: {lat}")
print (f"Longitude: {lon}")
print (f"Place ID: {place_id}")