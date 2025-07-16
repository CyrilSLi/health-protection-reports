# Built-in modules
import io, json
from datetime import datetime as dt, timezone as tz
from urllib.parse import quote_plus

# Third-party modules
from dateparser import parse as date_parse
import pdfplumber
import requests as r

# Try to load LXML or fallback to cET or ET
try:
    import lxml.etree as etree
except ImportError:
    try:
        import xml.etree.cElementTree as etree
    except ImportError:
        import xml.etree.ElementTree as etree

def pdf_rows (file):
    rows, output = [], []
    if isinstance (file, str):
        file = r.get (file)
        file.raise_for_status ()
        file = io.BytesIO (file.content)
    
    with pdfplumber.open (file) as pdf:
        for page in pdf.pages:
            for row in page.extract_table ():
                meaningful = tuple (i.strip () for i in row if i and i.strip ()) # Remove empty cells
                if meaningful and any ("mb" in i.lower () for i in meaningful): # Remove headers (without MB in address)
                    rows.append ((meaningful [0], ) + tuple (i.replace ("\n", " ") for i in meaningful [1 : ]))

    for i in rows:
        name, addr = [], i [0].split ("\n")
        while addr [0] == addr [0].upper (): # Names are in all caps
            name.append (addr.pop (0))
        name, addr = " ".join (name).strip (), " ".join (addr).strip ()
        if not name or not addr:
            raise ValueError (f"Invalid name and address {i [0]}")
        row = {
            "name": name,
            "addr": addr,
            "type": i [1]
        }

        if len (i) == 4: # Closures, no re-open date
            row.update ({
                "start": default_ts (i [2], "start"),
                "end": 2 ** 32 - 1,
                "info": {
                    "Closure date": i [2],
                    "Reason for closure": i [3]
                }
            })
        elif len (i) == 5: # Closures, with re-open date
            row.update ({
                "start": default_ts (i [2], "start"),
                "end": default_ts (i [3], "end"),
                "info": {
                    "Closure date": i [2],
                    "Re-open date": i [3],
                    "Reason(s)": i [4]
                }
            })
        elif len (i) == 6: # Convictions
            row.update ({
                "start": default_ts (i [2], "start"),
                "end": default_ts (i [3], "end"),
                "info": {
                    "Offense date": i [2],
                    "Conviction date": i [3],
                    "Reason(s)": i [4],
                    "Penalty": i [5]
                }
            })
        else:
            raise ValueError (f"Unknown row format {i}")

        output.append (row)
    return output

def maps_url (name, addr):
    headers = {
        "Connection": "keep-alive",
        "Host": "www.google.com",
        "Referer": "https://www.google.com/maps/search/?api=1&query=",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }
    maps = r.get ("https://www.google.com/maps/search/?api=1&query=" + quote_plus (name + " " + addr), headers = headers)
    maps.raise_for_status ()
    maps = maps.text
    url_start = maps.find (r'\"https://www.google.com/maps/preview/place/')
    if url_start == -1:
        if name == "":
            print (f"Warning: Address {addr} not found.")
            return
        return maps_url ("", addr) # Search by address only
    else:
        url_start += 2 # Skip leading quote
    url_end = url_start + maps [url_start : ].find (r'\"')
    url = maps [url_start : url_end].replace ("\\\\", "\\").encode ().decode ("unicode_escape")
    coord_start = url.find ("/@") + 2
    lat_end = coord_start + url [coord_start : ].find (",")
    lon_end = lat_end + 1 + url [lat_end + 1 : ].find (",")
    return {
        "url": url,
        "lat": float (url [coord_start : lat_end]),
        "lon": float (url [lat_end + 1 : lon_end])
    }

def default_ts (timestamp, kind):
    parsed = date_parse (timestamp)
    if parsed:
        return round (parsed.replace (tzinfo = tz.utc).timestamp ())
    elif kind == "start":
        print (f"Warning: Start date {timestamp} not valid")
        return 0
    elif kind == "end":
        print (f"Warning: End date {timestamp} not valid")
        return 2 ** 32 - 1
    else:
        raise ValueError (f"Unknown timestamp kind {kind}")

def main ():
    with open ("data.json") as f:
        data = json.load (f)
    rss = r.get ("https://www.gov.mb.ca/health/publichealth/environmentalhealth/protection/hpr.rss")
    rss.raise_for_status ()
    rss = etree.fromstring (rss.text)

    for i in rss.iter ("item"):
        title = i.find ("title").text.lower ()
        for j in ("closures", "convictions"):
            if j in title:
                title = j
                break
        else:
            raise ValueError (f"Unknown item {title}")

        timestamp = round (date_parse (i.find ("pubDate").text).replace (tzinfo = tz.utc).timestamp ())
        if timestamp <= data [title].get ("timestamp", 0):
            continue
        pdf_url = i.find ("link").text
        # items = pdf_rows (pdf_url)

        if title == "closures":
            items = pdf_rows (io.BytesIO (open ("/tmp/closures.pdf", "rb").read ()))
        else:
            items = pdf_rows (io.BytesIO (open ("/tmp/convictions.pdf", "rb").read ()))

        url_cache = {}
        for i in items [ : 5]:
            cache_key = i ["name"] + " " + i ["addr"]
            if cache_key in url_cache:
                i.update (url_cache [cache_key])
                continue
            url_data = maps_url (i ["name"], i ["addr"])
            if url is None:
                continue
            i.update (url_data)
            url_cache [cache_key] = url_data
            print (f"Added URL {url_data ['url']}")

        data [title] = {
            "timestamp": timestamp,
            "url": pdf_url,
            "items": items
        }

    with open ("data1.json", "w") as f: # ("data.json", "w") as f:
        json.dump (data, f, indent = 4, ensure_ascii = False)

if __name__ == "__main__":
    main ()
