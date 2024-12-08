from flask import Flask, render_template, request, redirect, url_for, flash
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime
from urllib.parse import urlparse, urlunparse
import requests
import MySQLdb
import csv
import os
import json
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
import re
import logging
import json
from sentiment import preprocess_text, sentiment

app = Flask(__name__)
app.secret_key = 'hehe150'

# Konfigurasi logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Fungsi untuk koneksi ke MySQL
def connect_db():
    try:
        conn = MySQLdb.connect(
            host="127.0.0.1",
            user="rootuser",
            passwd="rootpass",
            db="sentimenken_db"
        )
        return conn
    except MySQLdb.Error as e:
        logging.error(f"Error koneksi ke database: {e}")
        return None

#JSON Middleware
@app.template_filter('tojson')
def tojson_filter(data):
    return json.dumps(data)

# Fungsi scraping artikel

# Platform Internasional
def scrape_bbc_article(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.find('title').get_text() if soup.find('title') else 'No title available'
            article_body = soup.find('article')
            content = ' '.join([p.get_text() for p in article_body.find_all('p')]) if article_body else "No content available"
            publish_date = None
            time_tag = soup.find('time')
            if time_tag:
                date_text = time_tag.get_text().strip()
                try:
                    parsed_date = datetime.strptime(date_text, "%d %B %Y")
                    publish_date = parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    publish_date = None

            if not publish_date:
                json_script = soup.find('script', type='application/ld+json')
                if json_script:
                    try:
                        json_content = json.loads(json_script.string)
                        if 'datePublished' in json_content:
                            publish_date = json_content['datePublished'].split('T')[0]
                    except json.JSONDecodeError:
                        pass

            return title, content, publish_date
        else:
            logging.error(f"Failed to fetch URL {url} with status code {response.status_code}")
            return None, None, None
    except requests.RequestException as e:
        logging.error(f"Request error saat scraping {url}: {e}")
        return None, None, None
    
def scrape_businesstimes_article(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.find('title').get_text() if soup.find('title') else 'No title available'
            
            elements = soup.select(".body-content .relative p, "
                          ".body-content .relative h1, "
                          ".body-content .relative h2, "
                          ".body-content .relative h3, "
                          ".body-content .relative h4, "
                          ".body-content .relative h5, "
                          ".body-content .relative h6")
    
            # Process each element similar to the jQuery map function
            article_texts = []
            for element in elements:
                # Get text, trim whitespace, remove newlines/tabs, and convert to lowercase
                cleaned_text = element.get_text().strip()
                cleaned_text = ' '.join(cleaned_text.split())  # Removes \r\n\t and excessive spaces
                cleaned_text = cleaned_text.lower()
                article_texts.append(cleaned_text)
            
            # Join all texts with space
            content = ' '.join(article_texts)
            
            publish_date = None
            publish_datetime = soup.select_one('meta[name="article:published_time"]')
            if publish_datetime:
                try:
                    date_str = publish_datetime.get('content')
                    publish_date = date_str.split('T')[0]
                except (ValueError, AttributeError):
                    publish_date = None
            else:
                publish_date = None

            
            # throws error if publish_date or content is None, and if content < 300 characters
            if not publish_date or not content or len(content) < 300:
                logging.error(f"Failed to scrape URL {url}. Data is invalid.")
                raise ValueError("Invalid data scraped")


            return title, content, publish_date
        else:
            logging.error(f"Failed to fetch URL {url} with status code {response.status_code}")
            return None, None, None
    except requests.RequestException as e:
        logging.error(f"Request error saat scraping {url}: {e}")
        return None, None, None
    
def scrape_straitstimes_article(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # title
            title = soup.find('title').get_text() if soup.find('title') else 'No title available'
            title = title.replace(' | The Straits Times', '')
            
            elements = soup.select(".layout.layout--onecol p, "
                      ".layout.layout--onecol h1, "
                      ".layout.layout--onecol h2, "
                      ".layout.layout--onecol h3, "
                      ".layout.layout--onecol h4, "
                      ".layout.layout--onecol h5, "
                      ".layout.layout--onecol h6")
    
            # Process each element similar to the jQuery map function
            article_texts = []
            for element in elements:
                # Get text, trim whitespace, remove newlines/tabs, and convert to lowercase
                cleaned_text = element.get_text().strip()
                cleaned_text = ' '.join(cleaned_text.split())  # Removes \r\n\t and excessive spaces
                cleaned_text = cleaned_text.lower()
                article_texts.append(cleaned_text)
            
            # Join all texts with space
            content = ' '.join(article_texts)
            
            publish_date = None
            publish_datetime = soup.select_one('meta[property="article:published_time"]')
            if publish_datetime:
                try:
                    date_str = publish_datetime.get('content')
                    publish_date = date_str.split('T')[0]
                except (ValueError, AttributeError):
                    publish_date = None
            else:
                publish_date = None

            
            # throws error if publish_date or content is None, and if content < 300 characters
            if not publish_date or not content or len(content) < 300:
                logging.error(f"Failed to scrape URL {url}. Data is invalid.")
                raise ValueError("Invalid data scraped")


            return title, content, publish_date
        else:
            logging.error(f"Failed to fetch URL {url} with status code {response.status_code}")
            return None, None, None
    except requests.RequestException as e:
        logging.error(f"Request error saat scraping {url}: {e}")
        return None, None, None
    
def scrape_financialpost_article(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # title
            title = None
            title_meta_tag = soup.select_one('meta[property="og:title"]')
            if title_meta_tag:
                try:
                    title = title_meta_tag.get('content')
                except (ValueError, AttributeError):
                    title = None
            else:
                title = None
            
            # article content
            elements = soup.select(".article-content__content-group p:not(.visually-hidden), "
                      ".article-content__content-group h1:not(.visually-hidden), "
                      ".article-content__content-group h2:not(.visually-hidden), "
                      ".article-content__content-group h3:not(.visually-hidden), "
                      ".article-content__content-group h4:not(.visually-hidden), "
                      ".article-content__content-group h5:not(.visually-hidden), "
                      ".article-content__content-group h6:not(.visually-hidden)")
    
            # Process each element similar to the jQuery map function
            article_texts = []
            for element in elements:
                # Get text, trim whitespace, remove newlines/tabs, and convert to lowercase
                cleaned_text = element.get_text().strip()
                cleaned_text = ' '.join(cleaned_text.split())  # Removes \r\n\t and excessive spaces
                cleaned_text = cleaned_text.lower()
                article_texts.append(cleaned_text)
            
            # Join all texts with space
            content = ' '.join(article_texts)
            
            # publish date
            publish_date = None
            json_ld = soup.select_one('script[type="application/ld+json"]')
            if json_ld:
                try:
                    json_data = json.loads(json_ld.string)
                    date_str = json_data.get('datePublished')
                    if date_str:
                        publish_date = date_str.split('T')[0]
                except (ValueError, AttributeError, json.JSONDecodeError):
                    publish_date = None


            return title, content, publish_date
        else:
            logging.error(f"Failed to fetch URL {url} with status code {response.status_code}")
            return None, None, None
    except requests.RequestException as e:
        logging.error(f"Request error saat scraping {url}: {e}")
        return None, None, None

# Platform Nasional
def convert_indonesian_date(indonesian_date):
    month_mapping = {
        "Januari": "January", "Februari": "February", "Maret": "March",
        "April": "April", "Mei": "May", "Juni": "June",
        "Juli": "July", "Agustus": "August", "September": "September",
        "Oktober": "October", "November": "November", "Desember": "December"
    }
    for indo_month, eng_month in month_mapping.items():
        if indo_month in indonesian_date:
            return indonesian_date.replace(indo_month, eng_month)
    return indonesian_date

def remove_day_name(indonesian_date):
    day_names = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    for day in day_names:
        if day in indonesian_date:
            return indonesian_date.replace(day + ",", "").strip()
    return indonesian_date

def scrape_bisnis_article(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Mengambil judul artikel
            title = soup.find('title').get_text(strip=True) if soup.find('title') else 'No title available'
            
            # Mengambil isi artikel
            article_body = soup.find('article', class_='detailsContent')
            if article_body:
                content = ' '.join([p.get_text(strip=True) for p in article_body.find_all('p')])
            else:
                content = "No content available"
            
            # Mengambil tanggal publikasi
            publish_date = None
            date_tag = soup.find('div', class_='detailsAttributeDates')
            if date_tag:
                date_text = date_tag.get_text(strip=True).split('|')[0].strip()
                # Hapus nama hari
                date_text_without_day = remove_day_name(date_text)
                # Konversi bulan ke bahasa Inggris
                date_text_converted = convert_indonesian_date(date_text_without_day)
                try:
                    # Parsing tanggal setelah konversi
                    publish_date = datetime.strptime(date_text_converted, "%d %B %Y").strftime("%Y-%m-%d")
                except ValueError as e:
                    logging.error(f"Failed to parse date: {date_text} -> {e}")
                    publish_date = None

            # Return hasil scraping
            return title, content, publish_date
        else:
            logging.error(f"Failed to fetch URL {url} with status code {response.status_code}")
            return None, None, None
    except requests.RequestException as e:
        logging.error(f"Request error saat scraping {url}: {e}")
        return None, None, None

def scrape_kontan_article(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Mengambil judul artikel
            title = soup.find('title').get_text(strip=True) if soup.find('title') else 'No title available'

            # Mengambil isi artikel
            article_body = soup.find('div', class_='tmpt-desk-kon')
            content = None
            if article_body:
                paragraphs = article_body.find_all('p')
                # Menggabungkan semua paragraf menjadi satu string
                content = ' '.join([
                    p.get_text(strip=True) 
                    for p in paragraphs 
                    if not p.get_text(strip=True).startswith("Reporter:") and not p.get_text(strip=True).startswith("Editor:")
                ])

            # Mengambil tanggal publikasi
            publish_date = None
            date_tag = soup.find('div', class_='fs14 ff-opensans font-gray')
            if date_tag:
                date_text = date_tag.get_text(strip=True).split('/')[0].strip()  # Ambil hanya bagian tanggal
                date_text_without_day = remove_day_name(date_text)  # Hapus nama hari
                date_text_converted = convert_indonesian_date(date_text_without_day)  # Konversi bulan ke Inggris
                try:
                    # Parsing tanggal setelah konversi
                    publish_date = datetime.strptime(date_text_converted, "%d %B %Y").strftime("%Y-%m-%d")
                except ValueError as e:
                    logging.error(f"Failed to parse date: {date_text} -> {e}")
                    publish_date = None

            # Return hasil scraping
            return title, content, publish_date
        else:
            logging.error(f"Failed to fetch URL {url} with status code {response.status_code}")
            return None, None, None
    except requests.RequestException as e:
        logging.error(f"Request error saat scraping {url}: {e}")
        return None, None, None

def scrape_cnbc_article(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else 'No title available'

            # Extract publish date
            publish_date = None
            date_tag = soup.find('div', class_='text-cm text-gray')  # Adjust this selector as needed
            if date_tag:
                date_text = date_tag.get_text(strip=True)
                logging.debug(f"Raw date text found: {date_text}")
                try:
                    # Parse date with the correct format
                    publish_date = datetime.strptime(date_text, "%d %B %Y %H:%M").strftime("%Y-%m-%d")
                    logging.debug(f"Parsed publish date: {publish_date}")
                except ValueError as e:
                    logging.error(f"Failed to parse date: {date_text} -> {e}")
                    publish_date = None
            else:
                logging.warning("Date element not found. Setting publish_date to None.")
                publish_date = None

            # Extract content
            content = None
            article_body = soup.find('div', class_='detail-text')  # Adjust this selector as needed
            if article_body:
                paragraphs = article_body.find_all('p')
                content = ' '.join([p.get_text(strip=True) for p in paragraphs])
            else:
                content = "No content available"

            # Final validation
            if not title or not publish_date or not content:
                logging.warning(f"Invalid data extracted: title={title}, publish_date={publish_date}, content={content}")
                return None, None, None

            # **Return values in the order expected by save_raw_to_db: (title, content, publish_date)**
            return title, content, publish_date
        else:
            logging.error(f"Failed to fetch URL {url} with status code {response.status_code}")
            return None, None, None
    except requests.RequestException as e:
        logging.error(f"Request error while scraping {url}: {e}")
        return None, None, None

def scrape_viva_article(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title = soup.find('title').get_text(strip=True) if soup.find('title') else 'No title available'

            # Extract content
            content = None
            article_body = soup.find('div', class_='main-content-detail')
            if article_body:
                paragraphs = article_body.find_all('p')
                content = ' '.join([p.get_text(strip=True) for p in paragraphs])
            else:
                content = "No content available"

            # Extract publish date from content
            publish_date = None
            date_pattern = r'(\d{1,2}\s\w+\s\d{4})'
            match = re.search(date_pattern, content)
            if match:
                date_text = match.group(1)
                date_text = convert_indonesian_date(date_text)
                try:
                    publish_date = datetime.strptime(date_text, "%d %B %Y").strftime("%Y-%m-%d")
                    # Remove the date from content to avoid duplication
                    content = content.replace(match.group(0), '').strip()
                except ValueError as e:
                    logging.error(f"Failed to parse date: {date_text} -> {e}")

            return title, publish_date, content
        else:
            logging.error(f"Failed to fetch URL {url} with status code {response.status_code}")
            return None, None, None
    except requests.RequestException as e:
        logging.error(f"Request error while scraping {url}: {e}")
        return None, None, None

def scrape_katadata_article(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title using CSS selectors
        title_tag = soup.select_one('h1.detail-title.mb-4') or soup.select_one('h1.article__title') or soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else 'No title available'

        # Extract content
        content_div = soup.select_one('div.detail-body.mb-4') or soup.select_one('div.article__body')
        if content_div:
            paragraphs = content_div.find_all('p')
            content = ' '.join([p.get_text(strip=True) for p in paragraphs])
        else:
            content = "No content available"

        # Extract publication date
        date_tag = soup.select_one('div.detail-date.text-gray') or soup.select_one('div.article__date')
        if date_tag:
            date_text = date_tag.get_text(strip=True)
            date_text_clean = date_text.split(",")[0].strip()  # Remove time if present
            date_text_converted = convert_indonesian_date(date_text_clean)
            try:
                publish_date = datetime.strptime(date_text_converted, "%d %B %Y").strftime("%Y-%m-%d")
            except ValueError as e:
                logging.error(f"Failed to parse date: {date_text_converted} -> {e}")
                publish_date = None
        else:
            publish_date = None

        return title, content, publish_date
    except Exception as e:
        logging.error(f"Error scraping {url}: {e}")
        return None, None, None

# Scrap to DB
def save_raw_to_db(url, title, content, publish_date):
    conn = connect_db()
    if conn is None:
        logging.error("Koneksi database gagal. Tidak dapat menyimpan data mentah.")
        return
    try:
        cursor = conn.cursor()
        input_date = datetime.now()
        cursor.execute("""
            INSERT INTO news (input_date, url, publish_date, title, content)
            VALUES (%s, %s, %s, %s, %s)
        """, (input_date, url, publish_date, title, content))
        conn.commit()
        logging.info(f"Berhasil menyimpan data mentah untuk URL: {url}")
    except MySQLdb.Error as e:
        logging.error(f"Error saat menyimpan data mentah ke database: {e}")
    finally:
        cursor.close()
        conn.close()

# Fungsi untuk menyimpan data dengan analisis sentimen ke database
def save_to_db(url, title, content, publish_date):
    conn = connect_db()
    if conn is None:
        logging.error("Koneksi database gagal. Tidak dapat menyimpan data dengan sentimen.")
        return
    try:
        cursor = conn.cursor()
        input_date = datetime.now()
        clean_content = preprocess_text(content)
        if not clean_content:
            logging.warning(f"Konten setelah preprocessing kosong untuk URL: {url}")
            compound_score, sentiment_label = 0.0, 'Error'
        else:
            compound_score, sentiment_label = sentiment(clean_content)
        cursor.execute("""
            INSERT INTO news (input_date, url, publish_date, title, content, compound, sentiment)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (input_date, url, publish_date, title, content, compound_score, sentiment_label))
        conn.commit()
        logging.info(f"Berhasil menyimpan data dengan sentimen untuk URL: {url}")
    except MySQLdb.Error as e:
        logging.error(f"Error saat menyimpan data dengan sentimen ke database: {e}")
    finally:
        cursor.close()
        conn.close()

# Route untuk halaman utama
def get_average_compound_today():
    try:
        today = datetime.today().strftime('%Y-%m-%d')
        conn = connect_db()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT AVG(compound) 
                    FROM news 
                    WHERE DATE(publish_date) = %s
                """, (today,))
                result = cursor.fetchone()
                average_compound = result[0] if result[0] is not None else 0.0
            conn.close()
            return round(average_compound, 4)
        else:
            return 0.0
    except Exception as e:
        logging.error(f"Error calculating today's average compound score: {e}")
        return 0.0

@app.route('/')
def index():
    try:
        # Connect to the database
        conn = connect_db()
        if conn is None:
            flash('Koneksi database gagal.', 'danger')
            return render_template(
                'index.html',
                page="dashboard",
                total_data=0,
                sentiment_compound="No Data",
                sentiment_mode="No Data",
                average_compound_today=0.0,
                yield_data_count=0,
                yield_today=0.0,
                news_data=[],
                yield_data=[]
            )

        with conn.cursor() as cursor:
            # Determine the current page
            page = request.args.get('page', 'dashboard')

            # Initialize variables
            total_data = 0
            average_compound_today = 0.0
            sentiment_compound = "No Data"
            sentiment_mode = "No Data"
            yield_data_count = 0
            yield_today = "0.00"
            news_data = []
            yield_data = []

            if page == "dashboard":
                # Fetch total number of news data
                cursor.execute("SELECT COUNT(*) FROM news")
                total_data = cursor.fetchone()[0] if cursor.rowcount > 0 else 0

                # Fetch average compound score for today
                today_date = datetime.today().strftime('%Y-%m-%d')
                cursor.execute("SELECT AVG(compound) FROM news WHERE DATE(publish_date) = %s", (today_date,))
                average_compound_today = cursor.fetchone()[0] or 0.0
                sentiment_compound = (
                    "Positive" if average_compound_today > 0 else
                    "Negative" if average_compound_today < 0 else
                    "Neutral"
                )

                # Fetch sentiment mode for today
                cursor.execute("SELECT sentiment FROM news WHERE DATE(publish_date) = %s", (today_date,))
                sentiment_results = [row[0] for row in cursor.fetchall()]
                sentiment_mode = (
                    max(set(sentiment_results), key=sentiment_results.count) if sentiment_results else "No Data"
                )

                # Fetch yield data count
                cursor.execute("SELECT COUNT(*) FROM yields")
                yield_data_count = cursor.fetchone()[0] if cursor.rowcount > 0 else 0

                # Fetch today's yield percentage
                yield_today = get_yield_today()
                yield_today_percentage = yield_today * 100 if yield_today is not None else 0.0
                yield_today = f"{yield_today_percentage:.2f}"

            elif page == "data_management":
                # Fetch all news data for data management
                cursor.execute("SELECT id, title, publish_date, content FROM news ORDER BY id DESC")
                news_data = cursor.fetchall()

                # Fetch all yield data for data management
                cursor.execute("SELECT id, yield_date, yield_value FROM yields ORDER BY id DESC")
                yield_data = cursor.fetchall()

        conn.close()

        # Render the template with data for the active page
        return render_template(
            'index.html',
            page=page,
            total_data=total_data,
            average_compound_today=round(average_compound_today, 2),
            sentiment_compound=sentiment_compound,
            sentiment_mode=sentiment_mode,
            yield_data_count=yield_data_count,
            yield_today=yield_today,
            news_data=news_data,
            yield_data=yield_data
        )

    except Exception as e:
        logging.error(f"Error in index route: {e}")
        flash('Terjadi kesalahan saat mengambil data.', 'danger')
        return render_template(
            'index.html',
            page="dashboard",
            total_data=0,
            sentiment_compound="No Data",
            sentiment_mode="No Data",
            average_compound_today=0.0,
            yield_data_count=0,
            yield_today="0.00",
            news_data=[],
            yield_data=[]
        )


@app.route('/delete_news/<int:news_id>', methods=['POST'])
def delete_news(news_id):
    try:
        conn = connect_db()
        if conn is None:
            flash('Koneksi database gagal.', 'danger')
            return redirect(url_for('index', page='data_management'))

        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM news WHERE id = %s", (news_id,))
            conn.commit()

        conn.close()
        flash('Berita berhasil dihapus.', 'success')
    except Exception as e:
        logging.error(f"Error deleting news: {e}")
        flash('Terjadi kesalahan saat menghapus berita.', 'danger')

    return redirect(url_for('index', page='data_management'))


@app.route('/delete_yield/<int:yield_id>', methods=['POST'])
def delete_yield(yield_id):
    try:
        conn = connect_db()
        if conn is None:
            flash('Koneksi database gagal.', 'danger')
            return redirect(url_for('index', page='data_management'))

        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM yields WHERE id = %s", (yield_id,))
            conn.commit()

        conn.close()
        flash('Data yield berhasil dihapus.', 'success')
    except Exception as e:
        logging.error(f"Error deleting yield: {e}")
        flash('Terjadi kesalahan saat menghapus data yield.', 'danger')

    return redirect(url_for('index', page='data_management'))

@app.route('/view_yields')
def view_yields():
    try:
        conn = connect_db()
        if conn is None:
            flash("Database connection failed.", "danger")
            return render_template('yield.html', yield_data=None)

        with conn.cursor() as cursor:
            cursor.execute("SELECT id, created_at, yield_date, yield_value FROM yields ORDER BY created_at DESC")
            yield_data = cursor.fetchall()
            # Log the data to check if it's being fetched correctly
            print("Fetched Yield Data:", yield_data)

        conn.close()
        return render_template('yield.html', yield_data=yield_data)
    except Exception as e:
        logging.error(f"Error fetching yield data: {e}")
        flash("Failed to fetch yield data.", "danger")
        return render_template('yield.html', yield_data=None)

def get_yield_today():
    try:
        today = datetime.today().strftime('%Y-%m-%d')
        conn = connect_db()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT AVG(yield_value) 
                    FROM yields 
                    WHERE DATE(yield_date) = %s
                """, (today,))
                result = cursor.fetchone()
            conn.close()
            
            # Kembalikan nilai tanpa pembulatan awal, hanya dibulatkan saat akan ditampilkan
            return result[0] if result[0] is not None else 0.0
        else:
            return 0.0
    except Exception as e:
        logging.error(f"Error fetching today's yield data: {e}")
        return 0.0

def get_sentiment_mode_today():
    try:
        today = datetime.today().strftime('%Y-%m-%d')
        conn = connect_db()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT sentiment 
                    FROM news 
                    WHERE DATE(publish_date) = %s
                """, (today,))
                sentiments = [row[0] for row in cursor.fetchall()]
            conn.close()
            if sentiments:
                return max(set(sentiments), key=sentiments.count)  # Mode calculation
            else:
                return "No Data"
        else:
            return "Error"
    except Exception as e:
        logging.error(f"Error calculating sentiment mode: {e}")
        return "Error"

# Route untuk memproses URL dari user
@app.route('/submit', methods=['POST'])
def submit_url():
    platform = request.form.get('platform')  # Get platform from the dropdown
    url = request.form.get('url')  # Get URL from user input

    # Mapping for domain validation
    platform_domains = {
        "kontan": "kontan.co.id",
        "cnbcindonesia": "cnbcindonesia.com",
        "viva": "viva.co.id",
        "bisnis": "bisnis.com",
        "katadata": "katadata.co.id",
        "bbc": "bbc.com",
        "businesstimes": "businesstimes.com.sg",
        "straitstimes": "straitstimes.com",
        "financialpost": "financialpost.com"
    }

    # Validate URL
    if not url:
        flash('URL tidak boleh kosong.', 'danger')
        return redirect(url_for('index'))

    parsed_url = urlparse(url)
    if not parsed_url.netloc or platform_domains.get(platform) not in parsed_url.netloc:
        flash('URL tidak valid atau tidak sesuai dengan platform yang dipilih.', 'danger')
        return redirect(url_for('index'))

    # Database connection
    conn = connect_db()
    if conn is None:
        flash('Koneksi database gagal.', 'danger')
        return redirect(url_for('index'))

    try:
        with conn.cursor() as cursor:
            # Check if URL already exists in the database
            cursor.execute("SELECT COUNT(*) FROM news WHERE url = %s", (url,))
            if cursor.fetchone()[0] > 0:
                flash('URL artikel sudah ada di database.', 'warning')
                return redirect(url_for('index'))

            # Perform scraping based on platform
            try:
                if platform == "bbc":
                    title, content, publish_date = scrape_bbc_article(url)
                elif platform == "businesstimes":
                    title, content, publish_date = scrape_businesstimes_article(url)
                elif platform == "straitstimes":
                    title, content, publish_date = scrape_straitstimes_article(url)
                elif platform == "financialpost":
                    title, content, publish_date = scrape_financialpost_article(url)
                elif platform == "bisnis":
                    title, content, publish_date = scrape_bisnis_article(url)
                elif platform == "kontan":
                    title, content, publish_date = scrape_kontan_article(url)
                elif platform == "cnbcindonesia":
                    title, content, publish_date = scrape_cnbc_article(url)
                elif platform == "viva":
                    title, publish_date, content = scrape_viva_article(url)
                elif platform == "katadata":
                    title, content, publish_date = scrape_katadata_article(url)
                else:
                    flash('Scraping untuk platform ini belum didukung.', 'warning')
                    return redirect(url_for('index'))
            except Exception as e:
                logging.error(f"Error during scraping: {e}")
                flash('Terjadi kesalahan saat proses scraping. Periksa kembali URL atau platform.', 'danger')
                return redirect(url_for('index'))

            # Validate scraping results
            if not title or not content or not publish_date:
                flash('Data tidak valid. Periksa kembali URL-nya.', 'danger')
                logging.warning(f"Scraped data is invalid: title={title}, content={content}, publish_date={publish_date}")
                return redirect(url_for('index'))

            # Save to database
            try:
                save_raw_to_db(url, title, content, publish_date)
                flash('Berita berhasil di-scrape dan disimpan ke database.', 'success')
                logging.info(f"Data berhasil disimpan: URL={url}")
            except Exception as e:
                logging.error(f"Error saat menyimpan data ke database: {e}")
                flash('Gagal menyimpan data ke database.', 'danger')

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        flash(f'Terjadi kesalahan: {e}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('index'))

@app.route('/download_template/<template>', methods=['GET'])
def download_template(template):
    try:
        if template == 'news':
            csv_content = "publish_date,title,content,url\n"
            filename = "news_template.csv"
        elif template == 'yield':
            csv_content = "yield_date,yield_value\n"
            filename = "yield_template.csv"
        else:
            flash('Invalid template requested!', 'danger')
            return redirect(url_for('index'))
        
        # Create a response with the CSV content
        response = app.response_class(
            response=csv_content,
            status=200,
            mimetype='text/csv',
        )
        response.headers.set('Content-Disposition', 'attachment', filename=filename)
        return response
    except Exception as e:
        logging.error(f"Error creating template: {e}")
        flash('Failed to download template.', 'danger')
        return redirect(url_for('index'))

# Route upload CSV
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    try:
        csv_file = request.files['csv_file']
        csv_type = request.form.get('csv_type')  # Get the type of CSV (news or yield)
        
        if not csv_file or not csv_type:
            flash('No file or CSV type selected!', 'danger')
            return redirect(url_for('index'))

        # Read the uploaded CSV
        csv_data = csv_file.read().decode('utf-8').splitlines()
        reader = csv.reader(csv_data)
        next(reader)  # Skip header row

        conn = connect_db()
        if conn is None:
            flash('Database connection failed!', 'danger')
            return redirect(url_for('index'))

        with conn.cursor() as cursor:
            if csv_type == 'news':
                for row in reader:
                    publish_date, title, content, *optional = row

                    # Parsing tanggal
                    try:
                        if "-" in publish_date:  # Format YYYY-MM-DD
                            parsed_date = datetime.strptime(publish_date, "%Y-%m-%d")
                        elif "/" in publish_date:  # Format MM/DD/YYYY
                            parsed_date = datetime.strptime(publish_date, "%m/%d/%Y")
                        else:
                            raise ValueError("Unknown date format")
                        
                        publish_date = parsed_date.strftime("%Y-%m-%d")
                    except ValueError:
                        flash(f"Invalid date format: {publish_date}", 'danger')
                        continue

                    # Tambahkan input_date
                    input_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    # Ambil URL jika tersedia
                    url = optional[0] if optional else None  # Ambil elemen ke-4 jika ada, jika tidak kosongkan

                    # Masukkan data ke database
                    cursor.execute("""
                        INSERT INTO news (publish_date, title, content, url, input_date)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (publish_date, title, content, url, input_date))

            elif csv_type == 'yield':
                for row in reader:
                    yield_date, yield_value = row

                    # Parsing tanggal
                    try:
                        if "-" in yield_date:  # Format YYYY-MM-DD
                            parsed_date = datetime.strptime(yield_date, "%Y-%m-%d")
                        elif "/" in yield_date:  # Format MM/DD/YYYY
                            parsed_date = datetime.strptime(yield_date, "%m/%d/%Y")
                        else:
                            raise ValueError("Unknown date format")
                        
                        yield_date = parsed_date.strftime("%Y-%m-%d")
                    except ValueError:
                        flash(f"Invalid date format: {yield_date}", 'danger')
                        continue

                    # Ambil waktu saat ini untuk created_at
                    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    # Masukkan data ke tabel yields
                    cursor.execute("""
                        INSERT INTO yields (yield_date, yield_value, created_at)
                        VALUES (%s, %s, %s)
                    """, (yield_date, yield_value, created_at))
            conn.commit()

        flash(f'{csv_type.capitalize()} data uploaded successfully!', 'success')
    except Exception as e:
        logging.error(f"Error uploading CSV: {e}")
        flash('Failed to upload CSV.', 'danger')
    return redirect(url_for('index'))

# Route Input Yield
@app.route('/input_yield', methods=['POST'])
def input_yield():
    try:
        yield_value = request.form['yield_value']
        yield_date = request.form['yield_date']

        # Pastikan nilai input bisa diproses sebagai float, tanpa membatasi presisi
        try:
            yield_value = float(yield_value)  # Konversi ke float
        except ValueError:
            flash('Invalid yield value. Please enter a valid number.', 'danger')
            return redirect(url_for('index'))

        # Simpan ke database atau proses lebih lanjut
        conn = connect_db()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO yields (yield_date, yield_value) VALUES (%s, %s)",
                    (yield_date, yield_value)
                )
                conn.commit()
            conn.close()

        flash('Yield value added successfully!', 'success')
    except Exception as e:
        logging.error(f"Error adding yield: {e}")
        flash('Failed to add yield value.', 'danger')
    return redirect(url_for('index'))

# Untuk ke grafik yield vs compound
@app.route('/yield-data', methods=['GET'])
def get_yield_data():
    try:
        conn = connect_db()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT yield_date, yield_value FROM yields ORDER BY yield_date ASC")
                results = cursor.fetchall()
            conn.close()
        
        # Konversi data ke JSON
        data = [{"date": str(row[0]), "value": row[1]} for row in results]
        return json.dumps(data)
    except Exception as e:
        logging.error(f"Error fetching yield data: {e}")
        return json.dumps({"error": "Failed to fetch yield data"}), 500

# Route untuk menampilkan analisis sentimen
@app.route('/analytics', methods=['GET', 'POST'])
def view_analytics():
    if request.method == 'POST':  # Jika tombol Analyze New Data ditekan
        try:
            with connect_db() as conn:
                if conn is None:
                    flash('Koneksi database gagal.', 'danger')
                    return redirect(url_for('view_analytics'))

                with conn.cursor() as cursor:
                    # Ambil data mentah yang belum dianalisis
                    cursor.execute("""
                        SELECT id, content 
                        FROM news 
                        WHERE compound IS NULL AND sentiment IS NULL
                    """)
                    raw_data = cursor.fetchall()
                    logging.debug(f"Data untuk analisis: {len(raw_data)} baris")

                    if raw_data:
                        for row in raw_data:
                            news_id, content = row
                            logging.debug(f"Proses ID {news_id} - Raw Content: {content}")

                            # Validasi: Pastikan konten tidak kosong
                            if not content or not content.strip():
                                logging.warning(f"Konten kosong untuk ID {news_id}. Melewati analisis.")
                                cursor.execute("""
                                    UPDATE news
                                    SET compound = 0, sentiment = 'Error'
                                    WHERE id = %s
                                """, (news_id,))
                                continue

                            try:
                                # Preprocessing teks menggunakan fungsi dari sentiment.py
                                clean_content = preprocess_text(content)
                                logging.debug(f"ID {news_id} - Konten Bersih: {clean_content}")

                                if not clean_content.strip():
                                    logging.warning(f"Konten setelah preprocessing kosong untuk ID {news_id}.")
                                    cursor.execute("""
                                        UPDATE news
                                        SET compound = 0, sentiment = 'Error'
                                        WHERE id = %s
                                    """, (news_id,))
                                    continue

                                # Analisis sentimen menggunakan fungsi dari sentiment.py
                                compound_score = sentiment(clean_content)
                                sentiment_label = (
                                    'Positive' if compound_score >= 0.05 else
                                    'Negative' if compound_score <= -0.05 else
                                    'Neutral'
                                )
                                logging.debug(f"ID {news_id} - Compound Score: {compound_score}, Sentiment Label: {sentiment_label}")

                                # Simpan hasil ke database
                                cursor.execute("""
                                    UPDATE news
                                    SET compound = %s, sentiment = %s
                                    WHERE id = %s
                                """, (compound_score, sentiment_label, news_id))

                            except Exception as e:
                                # Log error jika analisis gagal
                                logging.error(f"Error pada ID {news_id}: {e}")
                                cursor.execute("""
                                    UPDATE news
                                    SET compound = 0, sentiment = 'Error'
                                    WHERE id = %s
                                """, (news_id,))
                                continue

                        # Simpan semua perubahan ke database
                        conn.commit()
                        logging.info("Komit perubahan ke database berhasil.")
                        flash('Analisis sentimen berhasil dilakukan!', 'success')
                    else:
                        logging.info("Tidak ada data baru untuk dianalisis.")
                        flash('Tidak ada data baru untuk dianalisis.', 'info')

            return redirect(url_for('view_analytics'))

        except Exception as e:
            logging.error(f"Error di view_analytics: {e}")
            flash('Terjadi kesalahan saat memproses data.', 'danger')
            return redirect(url_for('view_analytics'))

    else:  # GET request
        try:
            with connect_db() as conn:
                if conn is None:
                    flash('Koneksi database gagal.', 'danger')
                    return render_template('index.html', sentiment_data=[], page="analytics")
                with conn.cursor() as cursor:
                    # Ambil semua data dari database untuk ditampilkan di tabel
                    cursor.execute("""
                        SELECT title, 
                               IFNULL(compound, 'Pending') AS compound, 
                               IFNULL(sentiment, 'Pending') AS sentiment,
                               publish_date
                        FROM news 
                        ORDER BY input_date DESC
                    """)
                    sentiment_data = cursor.fetchall()
            return render_template('index.html', sentiment_data=sentiment_data, page="analytics")
        except Exception as e:
            logging.error(f"Error mengambil data untuk ditampilkan: {e}")
            flash('Terjadi kesalahan saat mengambil data.', 'danger')
            return render_template('index.html', sentiment_data=[], page="analytics")

# Chart Sentimen
@app.route('/analytics-data', methods=['GET'])
def analytics_data():
    try:
        with connect_db() as conn:
            if conn is None:
                return {"error": "Database connection failed"}, 500

            with conn.cursor() as cursor:
                # Fetch data compound score
                cursor.execute("""
                    SELECT publish_date, AVG(compound) as avg_compound
                    FROM news
                    WHERE compound IS NOT NULL
                    GROUP BY publish_date
                    ORDER BY publish_date ASC
                """)
                compound_data = cursor.fetchall()

                # Fetch yield data
                cursor.execute("""
                    SELECT yield_date, yield_value
                    FROM yields
                    ORDER BY yield_date ASC
                """)
                yield_data = cursor.fetchall()

        # Format data untuk frontend
        compound_chart_data = [{"date": str(row[0]), "compound": row[1]} for row in compound_data]
        yield_chart_data = [{"date": str(row[0]), "yield": row[1]} for row in yield_data]

        # Debug data yang diambil
        logging.debug(f"Compound Data: {compound_chart_data}")
        logging.debug(f"Yield Data: {yield_chart_data}")

        return {
            "compound_data": compound_chart_data,
            "yield_data": yield_chart_data
        }, 200
    except Exception as e:
        logging.error(f"Error fetching analytics data: {e}")
        return {"error": "Failed to fetch analytics data"}, 500

# Route untuk menampilkan semua berita
@app.route('/news')
def view_news():
    try:
        with connect_db() as conn:
            if conn is None:
                flash('Koneksi database gagal.', 'danger')
                return render_template('news.html', news_data=[])
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM news ORDER BY input_date DESC")
                news_data = cursor.fetchall()
        return render_template('news.html', news_data=news_data)
    except Exception as e:
        logging.exception("Terjadi error di route view_news:")
        flash('Terjadi kesalahan saat mengambil data.', 'danger')
        return render_template('news.html', news_data=[])

# Data Management
@app.route('/data_management')
def data_management():
    try:
        conn = connect_db()
        if conn is None:
            flash("Database connection failed.", "danger")
            return render_template('index.html', page='data_management', news_data=None, yield_data=None)

        with conn.cursor() as cursor:
            # Fetch data from the news and yields tables
            cursor.execute("SELECT id, title, publish_date, content FROM news")
            news_data = cursor.fetchall()

            cursor.execute("SELECT id, yield_date, yield_value FROM yields")
            yield_data = cursor.fetchall()

        conn.close()
        return render_template(
            'index.html', 
            page='data_management',  # Indicates the Data Management section should be displayed
            news_data=news_data, 
            yield_data=yield_data
        )
    except Exception as e:
        logging.error(f"Error fetching data for management: {e}")
        flash("Failed to fetch data.", "danger")
        return render_template('index.html', page='data_management', news_data=None, yield_data=None)

@app.route('/delete_data/<string:table>/<int:id>', methods=['POST'])
def delete_data(table, id):
    try:
        conn = connect_db()
        if conn is None:
            flash("Database connection failed.", "danger")
            return redirect(url_for('data_management'))

        with conn.cursor() as cursor:
            if table == "news":
                cursor.execute("DELETE FROM news WHERE id = %s", (id,))
            elif table == "yields":
                cursor.execute("DELETE FROM yields WHERE id = %s", (id,))
            conn.commit()

        conn.close()
        flash("Data deleted successfully.", "success")
    except Exception as e:
        logging.error(f"Error deleting data: {e}")
        flash("Failed to delete data.", "danger")

    return redirect(url_for('data_management'))

@app.route('/edit_data/<string:table>/<int:id>', methods=['GET', 'POST'])
def edit_data(table, id):
    if request.method == 'POST':
        new_data = request.form
        try:
            conn = connect_db()
            if conn is None:
                flash("Database connection failed.", "danger")
                return redirect(url_for('data_management'))

            with conn.cursor() as cursor:
                if table == "news":
                    cursor.execute(
                        "UPDATE news SET title = %s, content = %s WHERE id = %s",
                        (new_data['title'], new_data['content'], id)
                    )
                elif table == "yields":
                    cursor.execute(
                        "UPDATE yields SET yield_date = %s, yield_value = %s WHERE id = %s",
                        (new_data['yield_date'], new_data['yield_value'], id)
                    )
                conn.commit()

            conn.close()
            flash("Data updated successfully.", "success")
        except Exception as e:
            logging.error(f"Error updating data: {e}")
            flash("Failed to update data.", "danger")

        return redirect(url_for('data_management'))
    else:
        try:
            conn = connect_db()
            if conn is None:
                flash("Database connection failed.", "danger")
                return redirect(url_for('data_management'))

            with conn.cursor() as cursor:
                if table == "news":
                    cursor.execute("SELECT id, title, content FROM news WHERE id = %s", (id,))
                elif table == "yields":
                    cursor.execute("SELECT id, yield_date, yield_value FROM yields WHERE id = %s", (id,))
                data = cursor.fetchone()

            conn.close()
            return render_template('edit_data.html', table=table, data=data)
        except Exception as e:
            logging.error(f"Error fetching data for edit: {e}")
            flash("Failed to fetch data for editing.", "danger")
            return redirect(url_for('data_management'))

# Main entry point
if __name__ == '__main__':
    app.run(debug=True)
