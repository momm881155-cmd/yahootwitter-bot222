import requests
from bs4 import BeautifulSoup
import tweepy
import os
import json
import feedparser

# Twitter API認証
consumer_key = os.environ['API_KEY']
consumer_secret = os.environ['API_SECRET']
access_token = os.environ['ACCESS_TOKEN']
access_token_secret = os.environ['ACCESS_SECRET']

auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
api = tweepy.API(auth)

POSTED_FILE = 'posted.json'

# 投稿済みリンク読み込み
if os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, 'r') as f:
        posted_links = json.load(f)
else:
    posted_links = []

headers = {'User-Agent': 'Mozilla/5.0'}
new_posts = []

# Yahoo RSS取得
def fetch_yahoo_rss(feed_url, category):
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        if entry.link not in posted_links:
            og_image = fetch_og_image(entry.link)
            if not og_image:
                print("Yahoo記事 画像取得失敗:", entry.link)
                continue
            post_to_twitter(entry.title, entry.link, og_image, category)

# OGP画像取得関数
def fetch_og_image(url):
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        og_image = soup.find("meta", property="og:image")
        if og_image:
            return og_image['content']
    except Exception as e:
        print("画像取得エラー:", e)
    return None

# 各サイトスクレイピング関数
def scrape_site(name, url, list_selector, base_url=''):
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    articles = soup.select(list_selector)
    for a in articles[:5]:  # 直近5件のみ
        title = a.get_text(strip=True)
        link = a['href']
        if not link.startswith('http'):
            link = base_url + link
        if link not in posted_links:
            og_image = fetch_og_image(link)
            if not og_image:
                print(f"{name} 画像取得失敗:", link)
                continue
            post_to_twitter(title, link, og_image, name)

# Twitter投稿処理
def post_to_twitter(title, link, image_url, category):
    tweet_text = f"{title}\n{link}\n#{category}"
    img_data = requests.get(image_url).content
    with open('temp.jpg', 'wb') as handler:
        handler.write(img_data)
    try:
        media = api.media_upload('temp.jpg')
        api.update_status(status=tweet_text, media_ids=[media.media_id])
        print("投稿成功:", title)
        posted_links.append(link)
    except Exception as e:
        print("投稿失敗:", e)

# Yahooニュース (エンタメ・天気)
fetch_yahoo_rss('https://news.yahoo.co.jp/rss/topics/entertainment.xml', 'エンタメ')
fetch_yahoo_rss('https://news.yahoo.co.jp/rss/topics/weather.xml', '天気')

# スクレイピング対象サイト
scrape_site('ORICON', 'https://www.oricon.co.jp/news/', 'div.newsList a', 'https://www.oricon.co.jp')
scrape_site('モデルプレス', 'https://mdpr.jp/news', 'li.news__list--item a', 'https://mdpr.jp')
scrape_site('スポーツ報知', 'https://hochi.news/entertainment/', 'div.article a', 'https://hochi.news')
scrape_site('日刊スポーツ', 'https://www.nikkansports.com/entertainment/', 'div.topicsList a', 'https://www.nikkansports.com')

# 投稿済みリンク保存
with open(POSTED_FILE, 'w') as f:
    json.dump(posted_links, f)
