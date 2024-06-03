import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import time
import os

from dotenv import load_dotenv

load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
CSV_FILE_INFOCOM = 'database/notified_posts_infocom.csv'
CSV_FILE_SCATCH = 'database/notified_posts_scatch.csv'
CSV_FILE_DISU = 'database/notified_posts_disu.csv'
TIME_INTERVAL = 5


def check_new_posts_infocom():
    base_urls = [
        {'name': '학사', 'link': 'http://infocom.ssu.ac.kr/kor/notice/undergraduate.php'},
        {'name': '대학원', 'link': 'http://infocom.ssu.ac.kr/kor/notice/graduateSchool.php'}
    ]
    for url in base_urls:
        response = requests.get(url['link'])
        soup = BeautifulSoup(response.text, 'html.parser')

        posts = soup.find_all('div', class_='subject on')

        new_posts = []
        for post in posts:
            title_span = post.find('span')
            title = f"[{url['name']}] {title_span.text.strip('[대학원] ')}" if title_span else None
            link = post.find_parent('a')['href'] if post.find_parent('a') else ""
            full_link = f'http://infocom.ssu.ac.kr{link}' if link.startswith(
                '/') else link if link != "" else url['link']
            new_posts.append({'title': title, 'link': full_link})

    return new_posts


def check_new_posts_scatch():
    url = 'https://scatch.ssu.ac.kr/%ea%b3%b5%ec%a7%80%ec%82%ac%ed%95%ad/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    posts = soup.find_all('div', class_='notice_col3')
    new_posts = []
    for post in posts:
        title_span = post.find('span', class_='d-inline-blcok m-pt-5')
        title = title_span.text.strip() if title_span else ""
        link = post.find('a')['href'] if post.find('a') else ""
        full_link = link if link.startswith('http') else f'https://scatch.ssu.ac.kr{link}' if link != "" else url
        new_posts.append({'title': title, 'link': full_link})

    return new_posts


def check_new_posts_disu():
    base_urls = [
        'https://www.disu.ac.kr/community/notice?cidx=38',
        'https://www.disu.ac.kr/community/notice?cidx=42'
    ]

    new_posts = []

    for url in base_urls:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        posts = soup.select('#zcmsprogram > div > table > tbody > tr')
        for post in posts:
            title_td = post.select_one('td.title.noti-tit')
            if title_td:
                category = title_td.select_one('span.hidden-md-up')
                a_tag = title_td.find('a')
                title = f'{category.text.strip()} {a_tag.text.strip()}' if a_tag else ""
                link = a_tag['href'] if a_tag else ""
                full_link = link if link.startswith('http') else f'https://www.disu.ac.kr{link}'
                new_posts.append({'title': title, 'link': full_link})

    return new_posts


def send_slack_message(title, link, source, color):
    attachment = {
        "attachments": [
            {
                "fallback": title,
                "color": color,
                "title": f"{source}",
                "text": f"{title}\n\n<{link}|바로가기>" if link else f"{title}",
                "ts": datetime.now().timestamp()
            }
        ]
    }
    response = requests.post(SLACK_WEBHOOK_URL, json=attachment)
    if response.status_code != 200:
        raise ValueError(f'Request to Slack returned an error {response.status_code}, the response is: {response.text}')


def load_notified_posts(csv_file):
    notified_posts = set()
    try:
        with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                notified_posts.add(row[0])
    except FileNotFoundError:
        pass
    return notified_posts


def save_notified_posts(notified_posts, csv_file):
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for post in notified_posts:
            writer.writerow([post])


def notify_new_posts(new_posts, source, csv_file, color):
    notified_posts = load_notified_posts(csv_file)
    new_notifications = 0

    for post in new_posts:
        if post['link'] not in notified_posts:
            send_slack_message(post['title'], post['link'], source, color)
            notified_posts.add(post['link'])
            new_notifications += 1
            time.sleep(TIME_INTERVAL)

    if new_notifications == 0:
        send_slack_message("새로운 공지사항이 없습니다.", None, source, '#aaaaaa')

    save_notified_posts(notified_posts, csv_file)


if __name__ == "__main__":
    new_posts_infocom = check_new_posts_infocom()
    new_posts_scatch = check_new_posts_scatch()
    new_posts_disu = check_new_posts_disu()
    notify_new_posts(new_posts_infocom, "전자정보공학부", CSV_FILE_INFOCOM, '#941b22')
    time.sleep(TIME_INTERVAL)
    notify_new_posts(new_posts_scatch, "SSU:catch", CSV_FILE_SCATCH, '#016694')
    time.sleep(TIME_INTERVAL)
    notify_new_posts(new_posts_disu, "차세대반도체학과", CSV_FILE_DISU, '#2596be')
    print(f"Checked for new posts at {datetime.now()}")
