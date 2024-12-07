import pandas as pd
import re
import html
import nltk
import csv
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from nltk.tokenize import sent_tokenize
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# CLEANING
def preprocess_text(review):
    stop_factory = StopWordRemoverFactory()
    stopword = stop_factory.create_stop_word_remover()
    # Step 1: Fix encoding issues (e.g., replacing "â€™" with correct characters)
    try:
        review = review.encode('latin1', errors='ignore').decode('utf-8', errors='ignore')
    except UnicodeEncodeError:
        pass  # If there's an encoding error, skip this step

    # Step 2: Remove list brackets and leading/trailing quotes
    review = re.sub(r"^\[|\]$", "", review)  # Remove square brackets at the start and end
    review = review.replace("'", "")  # Remove single quotes

    # Step 3: Remove extra backslashes
    review = review.replace("\\", "")

    # Step 4: Remove commas followed by double or single quotes
    review = re.sub(r',["\']', '', review)

    # Step 5: Replace double commas with a single comma
    review = re.sub(r',+', ',', review)

    # Step 6: Remove any instances of ".,", ",.", or ",,"
    review = re.sub(r'\.,|,\.', '.', review)  # Replace ".,", ",." with a single period
    review = re.sub(r',,', ',', review)  # Replace ",," with a single comma

    # Step 7: Remove hashtags
    review = re.sub(r'#\w+', '', review)

    review = re.sub(r'@\w+', '', review)

    # Step 8: Remove URLs
    review = re.sub(r'http\S+', '', review)

    # Step 9: Remove emojis
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # emoticon
        u"\U0001F300-\U0001F5FF"  # simbol & dingbat
        u"\U0001F680-\U0001F6FF"  # transportasi & simbol map
        u"\U0001F700-\U0001F77F"  # simbol kuno
        u"\U0001F780-\U0001F7FF"  # simbol kuno tambahan
        u"\U0001F800-\U0001F8FF"  # simbol tanda batas
        u"\U0001F900-\U0001F9FF"  # emoticon tambahan
        u"\U0001FA00-\U0001FA6F"  # simbol musik
        u"\U0001FA70-\U0001FAFF"  # simbol musik tambahan
        u"\U00002702-\U000027B0"  # simbol karakter
        u"\U000024C2-\U0001F251"  # simbol katakter tambahan
        "]+", flags=re.UNICODE
    )
    review = emoji_pattern.sub(r'', review)

    # Step 10: Remove unwanted whitespace characters
    review = re.sub(r'\s+', ' ', review).strip()

    # Step 11: Decode HTML entities
    review = html.unescape(review)

    # Step 12: Remove HTML tags
    review = re.sub(r'<.*?>', '', review)

    # Step 13: Remove non-ASCII characters
    review = re.sub(r'[^\x00-\x7F]+', '', review)

    review = stopword.remove(review)

    return review.strip()

#SENTIMENT
file_path = 'lexicon_fix.csv'
inset_lexicon = {}

with open(file_path, encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile, delimiter=";")
    next(reader)
    for row in reader:
        word = row[0]
        score = float(row[1]) 
        inset_lexicon[word] = score

# Sentiment analysis using the updated lexicon
def sentiment(text):
    analyzer = SentimentIntensityAnalyzer()

    analyzer.lexicon.update(inset_lexicon)
    sentence_list = nltk.sent_tokenize(text)
    
    total_compound = 0.0
    for sentence in sentence_list:
        sentiment_scores = analyzer.polarity_scores(sentence)
        compound = sentiment_scores['compound']
        total_compound += compound
    average_compound = total_compound / len(sentence_list) if sentence_list else 0
    
    return round(average_compound, 4)

#Function for Preprocessing and Sentiment
def data_prep(df):
    df['clean'] = df['content'].apply(preprocess_text)
    df = df[df['clean'].notna()]
    df["compound"] = df['clean'].apply(sentiment)
    df = df[["id", "clean", "compound"]]
    return df
