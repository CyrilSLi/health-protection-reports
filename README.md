# health-protection-reports

A website which displays Manitoba [Health Protection Reports](https://www.gov.mb.ca/health/publichealth/surveillance/reports.html) PDF data on a user-friendly map. This data includes restaurants, pools, and other locations which have been shut down and/or convicted for violating health regulations.

`main.py` is a Python script which should be run periodically to update the data, which is saved in `data.js` (a JSON object with a JavaScript wrapper). The entire website is contained in a single static HTML file, `index.html`, which reads the data from `data.js` using a `<script>` tag.

## Updating the Data

```
pip install -r requirements.txt
python main.py
```

use `python main.py -f` to always fetch the PDFs, even when they haven't changed as indicated by the [RSS feed](https://www.gov.mb.ca/health/publichealth/environmentalhealth/protection/hpr.rss).
