""" from pypdf import PdfReader
reader = PdfReader ("/tmp/closures.pdf")
page = reader.pages [0]
def visitor (text, *args, **kwargs):
    print ("Visiting", text)
    return True
print (page.extract_text (visitor_text = visitor)) """

import pdfplumber
import texttable
import shutil

def convictions():
    pass
with pdfplumber.open ("/tmp/convictions.pdf") as pdf:
    table = texttable.Texttable (shutil.get_terminal_size ().columns)
    page = pdf.pages [0]
    for i in page.extract_table (table_settings = {}):
        table.add_row (tuple (str (j).replace ("\n", " ") for j in i))
    print (table.draw ())

req = r.get ("https://www.google.com/maps/search/?api=1&query=A%2B%20SUSHI%20JAPANESE%0ARESTAURANT%0A631%20Corydon%20Avenue%0AWinnipeg%2C%20MB")
req = req.text
url_start = req.find (r'\"https://www.google.com/maps/preview/place') + 2
url_end = url_start + req [url_start : ].find ("ChIJZyKAwLLYwVIR4yjKeeKSLMk") + 100 # (r'\"') - 2
print (req [url_start : url_end])