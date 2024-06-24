import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import time
import os

from dotenv import load_dotenv

load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
csv_links = {'INFOCOM': '/home/suhohan/SSU_notice_alert/database/notified_posts_infocom.csv',
             'INFOCOM_GRAD': '/home/suhohan/SSU_notice_alert/database/notified_posts_infocom_grad.csv',
             'SCATCH': '/home/suhohan/SSU_notice_alert/database/notified_posts_scatch.csv',
             'DISU': '/home/suhohan/SSU_notice_alert/database/notified_posts_disu.csv', }


def check_new_posts_infocom():
    url_origin = 'http://infocom.ssu.ac.kr/kor/notice/undergraduate.php'

    response = requests.get(url_origin)
    soup = BeautifulSoup(response.text, 'html.parser')

    posts = soup.find_all('div', class_='subject on')

    new_posts = []
    for post in posts:
        title_span = post.find('span')
        title = title_span.text if title_span else None
        link = post.find_parent('a')['href'] if post.find_parent('a') else ""
        full_link = f'http://infocom.ssu.ac.kr{link}' if link.startswith(
            '/') else link if link != "" else url_origin
        new_posts.append({'title': title, 'link': full_link})

    return new_posts


def check_new_posts_infocom_grad():
    url_origin = 'http://infocom.ssu.ac.kr/kor/notice/graduateSchool.php'
    response = requests.get(url_origin)
    soup = BeautifulSoup(response.text, 'html.parser')

    posts = soup.find_all('div', class_='subject on')

    new_posts = []
    for post in posts:
        title_span = post.find('span')
        title = title_span.text if title_span else None
        link = post.find_parent('a')['href'] if post.find_parent('a') else ""
        full_link = f'http://infocom.ssu.ac.kr{link}' if link.startswith(
            '/') else link if link != "" else url_origin
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


def send_slack_message(attachments):
    response = requests.post(SLACK_WEBHOOK_URL, json={"attachments": attachments})
    if response.status_code != 200:
        raise ValueError(f'Request to Slack returned an error {response.status_code}, the response is: {response.text}')


def load_notified_posts(csv_file):
    notified_posts = set()
    if os.path.exists(csv_file):
        with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            notified_posts = set(row[0] for row in reader)

    return notified_posts


def save_notified_posts(notified_posts, csv_file):
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for post in notified_posts:
            writer.writerow([post])


def notify_new_posts(new_posts, source, csv_file, color):
    notified_posts = load_notified_posts(csv_links[csv_file])
    new_notifications = []
    for post in new_posts:
        if post['link'] and post['link'] not in notified_posts:
            new_notifications.append({
                "fallback": post['title'],
                "color": color,
                "title": f"{source}",
                "text": f"{post['title']}\n\n<{post['link']}|바로가기>" if post['link'] else f"{post['title']}",
                "ts": datetime.now().timestamp()
            })
            notified_posts.add(post['link'])

    save_notified_posts(notified_posts, csv_links[csv_file])
    return new_notifications


if __name__ == "__main__":
    attachments = []
    attachments.extend(notify_new_posts(check_new_posts_infocom(), "전자정보공학부 학사", 'INFOCOM', '#941b22'))
    attachments.extend(notify_new_posts(check_new_posts_infocom_grad(), "전자정보공학부 대학원", 'INFOCOM_GRAD', '#941b22'))
    attachments.extend(notify_new_posts(check_new_posts_scatch(), "SSU:catch", 'SCATCH', '#016694'))
    attachments.extend(notify_new_posts(check_new_posts_disu(), "차세대반도체학과", 'DISU', '#2596be'))

    if attachments:
        send_slack_message(attachments)
    else:
        send_slack_message([{
            "fallback": "새로운 공지사항이 없습니다.",
            "color": '#aaaaaa',
            "title": "공지사항",
            "text": "새로운 공지사항이 없습니다.",
            "ts": datetime.now().timestamp()
        }])

    print(f"Checked for new posts at {datetime.now()}")
