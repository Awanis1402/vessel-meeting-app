# vessel-meeting-app
Web simple untuk upload CSV/XLSX harian dan detect vessel yang bertemu dalam jarak 100 meter ke bawah.
Features
Upload CSV atau XLSX
Pilih column masa, kapal, latitude, longitude, speed/SOG
Filter kawasan tertentu guna lat/lon
Setting jarak maksimum, time window dan speed maksimum
Output table Summary Meeting
Output table Raw Detection Detail
Download result CSV
Run Local
```bash
pip install -r requirements.txt
streamlit run app.py
```
Deploy Streamlit Cloud
Upload `app.py` dan `requirements.txt` ke GitHub repo.
Buka Streamlit Community Cloud.
Connect GitHub repo.
Pilih file utama: `app.py`.
Deploy.
Setting cadangan
Distance: 100 meter
Time window: 10 minit
Speed/SOG: 1 knot
Minimum detection untuk Confirmed: 2
