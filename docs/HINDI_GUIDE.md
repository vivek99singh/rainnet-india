# RainNet India कैसे चलाएँ

यह experimental India workflow है। India में trained या verified weather service अभी नहीं है।

## 1. बिना radar access के demo

Python 3.12 install होना चाहिए। Repository download/clone करके उसका folder terminal में खोलें। Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m rainnet_india.cli demo --city mumbai
Start-Process output/demo/report.html
```

किसी account, API key या paid service की जरूरत नहीं। Packages पहली बार download होते हैं; उसके बाद demo offline चलता है।

**यह synthetic demo है:** बारिश के आँकड़े बनाए गए हैं। Persistence baseline आखिरी frame दोहराता है; इसमें AI नहीं चलता। Video में `SYNTHETIC DEMO / NOT AI` label रहने दें। इसे आज की Mumbai की बारिश न बताएँ।

दूसरे presets: `delhi`, `bengaluru`, `chennai`, `kolkata`, `hyderabad`, `pune`।

## 2. असली RainNet model जाँचें

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-model.txt
.\.venv\Scripts\python.exe scripts/download_model.py
.\.venv\Scripts\python.exe scripts/validate_upstream.py
```

Model लगभग 310 MB है; TensorFlow का अलग बड़ा download होता है। CPU पर चल सकता है। Weights और `.venv` GitHub पर upload नहीं होते। यह test German sample पर होता है। `output/upstream-validation/metrics.json` में model और persistence की errors आती हैं। एक German sample India की accuracy सिद्ध नहीं करता।

## 3. India radar experiment

[Data guide](INDIA_DATA.md) के मुताबिक calibrated, quality-controlled data तैयार करें। चार observations 5-5 मिनट के अंतर पर चाहिए। Radar screenshots, dBZ values या city forecast API का JSON सीधे नहीं दे सकते।

```powershell
.\.venv\Scripts\python.exe -m rainnet_india.cli predict --input india-data/mumbai.npz --city mumbai --threshold-mmh 1
Start-Process output/prediction/report.html
```

पुराने data के लिए `--archive` जोड़ें। Report में `ARCHIVE REPLAY` आएगा। Code अपने-आप IMD data download नहीं करता; authorized access और usable calibrated data अभी arrange करना होगा।

## 4. Result समझें

- Time IST में है। Lead आखिरी scan से गिनी जाती है, script शुरू करने के समय से नहीं।
- mm/h बारिश की intensity है, पाँच मिनट में गिरे पानी की मात्रा नहीं।
- Threshold crossing का मतलब “ठीक पाँच मिनट बाद बारिश शुरू होगी” नहीं।
- Console में local research alert आता है; phone/WhatsApp/Telegram message नहीं भेजता।
- Invalid input पर code रुकता है। Error को “बारिश नहीं होगी” न समझें।

## 5. Reel में सही दावा

“यह open-source AI radar scans से आगे की बारिश का अनुमान लगाता है। मैंने इसमें India के data के लिए checks, city presets और IST report जोड़ा है। Model अभी Germany-trained है; India की accuracy जाँचना बाकी है।”

Synthetic demo पर कहें: “यह workflow समझाने का demo है; live weather forecast नहीं।” कोई अभिनेत्री की reel या copyrighted footage repository में शामिल नहीं है।

## Troubleshooting

| Error | अगला कदम |
|---|---|
| `No module named ...` | इसी project की `.venv` का Python इस्तेमाल करें। |
| `older than 10 minutes` | नया scan लाएँ; historical experiment में `--archive` लगाएँ। |
| `mm/h` / `1 km` | Calibration/units/grid सुधारें; केवल metadata बदलकर error न छिपाएँ। |
| `outside radar coverage` | उस city को cover करने वाला grid दें। |
| `Missing/negative rain data` | Provider QC जाँचें। Missing pixels को zero न मानें। |
| Checksum mismatch | Linked Zenodo regression model लें; incomplete download को weights न समझें। |

अगला चरण: authorized radar feed → provider-specific QC/gridding → Indian events पर baseline comparison → fine-tuning/held-out tests → false alarms और missed rain की measurement → opt-in phone alerts। Live feed, Indian evaluation और phone delivery अभी पूरे नहीं हुए हैं।
