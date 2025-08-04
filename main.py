import feedparser
import tweepy
import os
import json
import requests
from bs4 import BeautifulSoup
import re

POSTED_FILE = 'posted.json'

consumer_key = os.environ['API_KEY']
consumer_secret = os.environ['API_SECRET']
access_token = os.environ['ACCESS_TOKEN']
access_token_secret = os.environ['ACCESS_SECRET']

auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
api = tweepy.API(auth)

if os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, 'r') as f:
        posted_links = json.load(f)
else:
    posted_links = []

rss_feeds = [
    ('https://news.yahoo.co.jp/rss/topics/entertainment.xml', 'エンタメ'),
    ('https://news.yahoo.co.jp/rss/topics/weather.xml', '天気')
]

new_posts = []

def generate_hashtags(title, category):
    hashtags = [f"#{category}"]
    if '雨' in title or '降水' in title or '大雨' in title:
        hashtags.append("#雨情報")
    if '芸能' in title or '俳優' in title or 'アイドル' in title:
        hashtags.append("#芸能")
    return ' '.join(hashtags)

def fetch_og_image(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        og_image = soup.find("meta", property="og:image")
        if og_image:
            return og_image['content']
    except Exception as e:
        print("画像取得エラー:", e)
    return None

for feed_url, category in rss_feeds:
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        if entry.link not in posted_links:
            if category == '天気' and not re.search(r'雨|降水|大雨', entry.title):
                continue

            image_url = fetch_og_image(entry.link)
            if not image_url:
                print("画像が取得できませんでした。スキップします。")
                continue

            hashtags = generate_hashtags(entry.title, category)
            tweet_text = f"{entry.title}\n{entry.link}\n{hashtags}"

            img_data = requests.get(image_url).content
            with open('temp.jpg', 'wb') as handler:
                handler.write(img_data)

            try:
                media = api.media_upload('temp.jpg')
                api.update_status(status=tweet_text, media_ids=[media.media_id])
                print("画像付き投稿完了:", tweet_text)
                new_posts.append(entry.link)
            except Exception as e:
                print("投稿エラー:", e)

if new_posts:
    posted_links.extend(new_posts)
    with open(POSTED_FILE, 'w') as f:
        json.dump(posted_links, f)
else:
    print("新着記事なし。")
