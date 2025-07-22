# Built-in modules
import io, json, os, sys
from datetime import timezone as tz
from hashlib import sha256
from urllib.parse import quote_plus

# Third-party modules
from dateparser import parse as date_parse
import pdfplumber
import requests as r

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

url_cache, hash = {}, None

def open_data ():
    prefix = "window.healthData = "
    try:
        with open ("data.js") as f:
            f.read (len (prefix))
            return json.loads (f.read ())
    except FileNotFoundError:
        try:
            with open ("data.json") as f:
                return json.load (f)
        except FileNotFoundError:
            return {
                "closures": {
                    "name": "Closure",
                    "timestamp": 0
                },
                "convictions": {
                    "name": "Conviction",
                    "timestamp": 0
                }
            }

def save_data (data, write = True):
    global hash
    dump = json.dumps (data, indent = 1, ensure_ascii = False)
    if write:
        with open ("data.js", "w") as f:
            f.write ("window.healthData = ")
            f.write (dump)
    else:
        hash = sha256 (dump.encode ("utf-8")).hexdigest ()

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
                    "Reason(s)": i [3]
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

def maps_url (item, name = True):
    global url_cache
    if "maps" in item or "mobile food unit" in item ["addr"].lower ():
        return
    cache_key = item ["name"] + " " + item ["addr"]
    if cache_key in url_cache:
        item ["maps"] = url_cache [cache_key]
        return

    headers = {
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/maps/search/?api=1&query=",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }
    maps = r.get ("https://www.google.com/maps/search/?api=1&query=" + quote_plus ((item ["name"] + " " if name else "") + item ["addr"]), headers = headers)
    maps.raise_for_status ()
    maps = maps.text
    url_start = maps.find (r'\"https://www.google.com/maps/preview/place/')
    if url_start == -1:
        if not name:
            print (f"Warning: Address {item ['addr']} not found.")
        else:
            maps_url (item, False) # Search by address only
        return
    else:
        url_start += 2 # Skip leading quote
    url_end = url_start + maps [url_start : ].find (r'\"')
    url = maps [url_start : url_end].replace ("\\\\", "\\").encode ().decode ("unicode_escape")
    coord_start = url.find ("/@") + 2
    lat_end = coord_start + url [coord_start : ].find (",")
    lon_end = lat_end + 1 + url [lat_end + 1 : ].find (",")
    item ["maps"] = {
        "url": url,
        "lat": float (url [coord_start : lat_end]),
        "lon": float (url [lat_end + 1 : lon_end])
    }
    url_cache [cache_key] = item ["maps"]
    return True

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
    data = open_data ()
    rss = r.get ("https://www.gov.mb.ca/health/publichealth/environmentalhealth/protection/hpr.rss")
    rss.raise_for_status ()
    rss = etree.fromstring (rss.text)

    for file in rss.iter ("item"):
        title = file.find ("title").text.lower ()
        for j in ("closures", "convictions"):
            if j in title:
                title = j
                break
        else:
            raise ValueError (f"Unknown item {title}")

        timestamp = round (date_parse (file.find ("pubDate").text).replace (tzinfo = tz.utc).timestamp ())
        prev_items = data [title].get ("items")
        if timestamp > data [title].get ("timestamp", 0) or not prev_items or sys.argv [1 : ] in (["--force"], ["-f"]):
            pdf_url = file.find ("link").text
            data [title].update ({
                "timestamp": timestamp,
                "url": pdf_url
            })

            prev_hash = set ()
            for i in data [title].setdefault ("items", []):
                item = i.copy ()
                item.pop ("maps", None)
                prev_hash.add (json.dumps (item, sort_keys = True))
            new_items = pdf_rows (pdf_url)

            new_count = 0
            def overwrite (keys, item, items):
                nonlocal new_count
                dups = tuple (i for i in items if all (i.get (k) == item [k] for k in keys))
                if len (dups) > 1:
                    print (f"Warning: Multiple items with keys {({i: item [i] for i in keys})} found, stopping overwrite")
                elif len (dups) == 1:
                    print (f"Overwriting item with keys {({i: item [i] for i in keys})}")
                    items.remove (dups [0])
                    items.insert (0, item)
                    new_count += 1
                else:
                    return True

            for i in new_items:
                if json.dumps (i, sort_keys = True) in prev_hash: # Identical
                    continue
                if overwrite (("name", "addr", "type", "start"), i, prev_items):
                    maps_url (i)
                    if overwrite (("maps", "start"), i, prev_items): # New item
                        prev_items.insert (0, i)
                        new_count += 1
            print (f"Added {new_count} new items to {title} ({len (data [title] ['items'])} total)")
            save_data (data)

        for i in data [title] ["items"]:
            if maps_url (i):
                save_data (data)
                print (f"Added URL {i ['maps'] ['url']}")

    script_tag = '<script src="data.js?v='
    save_data (data, False) # get hash
    with open (os.path.join (os.path.dirname (os.path.abspath (__file__)), "index.html"), "r+") as f:
        line = ""
        while script_tag not in line:
            pointer = f.tell ()
            line = f.readline ()
        index = line.find (script_tag) + len (script_tag)
        f.seek (pointer)
        f.write (line.replace (line [index : index + 64], hash))

if __name__ == "__main__":
    main ()
