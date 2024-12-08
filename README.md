# Surat Utang Negara (SUN) Sentiment Dashboard by Institut Teknologi Sepuluh Nopember

Projek ini dibuat berdasarkan kerjasama antara Kementerian Keuangan Republik Indonesia dengan Departemen Statistik Institut Teknologi Sepuluh Nopember (ITS), Surabaya mengenai relasi antara sentimen media massa dengan pergerakan yield Surat Utang Negara (SUN) Indonesia.

## Tech Stack

- Database: MySQL ver. 8.0
- Web App: Flask ver. 3.1

untuk detail dependecies yang digunakan, untuk database dapat dilihat pada `docker-compose.yaml` dan Web App dapat dilihat di `pyproject.toml`

## Run Database MySQL

1. Setting sesuaikan kebutuhan server anda file `docker-compose.yaml`, seperti setting lokasi volume, port, username, password, dll.
2. Lakukan command `docker compose up -d` atau gunakan GUI untuk menjalankan docker compose.
3. Pastikan database sudah terjalankan dengan menjalankan `docker ps` atau cek melalui GUI, lalu tes koneksi terhadap database sudah bisa terjalin.

## Run Flask Web App

### Development

Untuk development, kami sarankan menggunakan `uv` yang dapat dicek di [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/).

1. Setup `venv`. Apabila menggunakan `uv` jalankan `uv venv`
2. Aktifkan `venv` dengan menjalankan:

```
# On Windows
.\.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

3. Install dependencies dengan menjalankan `uv sync`
4. Jalankan command `uv run -- flask run -p 3000`

### Deployment

Cek dokumentasi Flask pada [https://flask.palletsprojects.com/en/stable/tutorial/deploy/](https://flask.palletsprojects.com/en/stable/tutorial/deploy/).
