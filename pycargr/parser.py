#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

__author__ = 'Florents Tselai'

from typing import Iterable
from datetime import datetime
from urllib.request import urlopen, Request

from bs4 import BeautifulSoup, Tag, PageElement
from fake_useragent import UserAgent

from pycargr.model import Car


class SearchResultPageParser:
    def __init__(self, search_page_url):
        self.search_page_url = search_page_url
        req = Request(
            search_page_url,
            data=None,
            headers={
                'User-Agent': UserAgent().chrome
            }
        )
        self.html = urlopen(req).read().decode('utf-8')
        self.soup = BeautifulSoup(self.html, 'html.parser')
        self.num_results = None
        for f in self.soup.find_all('strong'):
            if 'αγγελίες' in f.text:
                if f.text.split()[0].isdigit():
                    self.num_results = int(f.text.split()[0])

    def parse(self):
        for a in self.soup.find_all('a', class_='row-anchor'):
            yield str(int(a.get('href').replace('/', '').split('-')[0].replace('classifiedscarsview', '')))

    def __len__(self):
        return self.num_results


class CarItemParser:
    CAR_FIELDS = {
        'bhp': 'Ίπποι',
        'release_date': 'Χρονολογία',
        'fuel_type': 'Καύσιμο',
        'displacement': 'Κυβικά',
        'milage': 'Χιλιόμετρα',
        'status': 'Κατάσταση',
        'price': 'Τιμή',
        'id': 'Νούμεροαγγελίας',
        'transmission': 'Σασμάν',
        'color': 'Χρώμα',
        'drivetrain': 'Κίνηση',
        'visits': 'Εμφανίσειςαγγελίας',
        'euro_class': 'Κλάσηρύπων',
        'registration': 'Τέληκυκλοφορίας'
    }

    def __init__(self, car_id):
        self.car_id = car_id
        self.req = Request(
            'https://www.car.gr/%s#bigger-photos' % self.car_id,
            data=None,
            headers={
                'User-Agent': UserAgent().chrome
            }
        )
        self.html = urlopen(self.req).read().decode('utf-8')
        self.soup = BeautifulSoup(self.html, 'html.parser')

    def _set_table_field(self, car: Car, key: str, val: str) -> None:
        result = self.find_attr_row(val)
        final_value = result.text.replace("\n", "").strip() if result else None
        setattr(car, key, final_value)

    def get_spec_table_rows(self) -> Iterable[PageElement]:
        return self.soup.find('table', attrs={'id': 'specification-table'}).find("tbody").children

    def find_attr_row(self, attr: str) -> Tag | None:
        rows = self.get_spec_table_rows()
        def locate_row(row: Tag) -> bool:
            if children := row.children:
                txts = {child.text.replace(" ", "").replace("\n", "") for child in children}
                return attr in txts
            return False
        results = list(filter(locate_row, rows))
        if results:
            return list(results[0].children)[-1]
        return None

    def parse_title(self):
        try:
            return self.soup.find('title').text
        except Exception:
            return None

    def parse_description(self):
        try:
            return self.soup.find(itemprop='description').text.replace("\n", "").replace("\r", "")
        except Exception:
            return None

    def parse_city(self):
        try:
            return self.soup.find('span', itemprop='addressLocality').text
        except Exception:
            return None

    def parse_region(self):
        try:
            return self.soup.find('span', itemprop='addressRegion').text

        except Exception:
            return None

    def parse_postal_code(self):
        try:
            return int(self.soup.find('span', itemprop='postalCode').text)

        except Exception:
            return None

    def parse_images(self):
        img_request = self.req
        img_request.full_url = img_request.full_url + "#"
        try:
            images_urls = []
            for img in self.soup.find_all('img', class_='thumb-img'):
                images_urls.append(img.get('src').replace(r'//', 'https://').replace('_v', '_b'))
            return images_urls
        except Exception:
            return None

    def parse_seller_info(self) -> dict:
        seller = {}

        main_seller_info = self.soup.find('div', attrs={'class': 'main-seller-info'})

        if not main_seller_info:
            print(f'No main seller info found for car {self.car_id}')
            return {}

        seller_anchor = main_seller_info.find('a', attrs={'target': '_blank'})
        seller['link'] = seller_anchor.attrs['href'] if 'href' in seller_anchor else None
        seller['name'] = seller_anchor.attrs['title'] if seller_anchor else None

        seller_span = main_seller_info.find("span")

        try:
            seller['region'], seller['zip_code'] = seller_span.text.split() if seller_span else (None, None)
        except ValueError:
            print(seller_span.text)

        return seller

    def parse(self) -> Car:
        c = Car(self.car_id)

        # Generic Info
        c.title = self.parse_title()
        c.url = self.req.full_url
        c.description = self.parse_description()

        # Car Specs
        for field, value in self.CAR_FIELDS.items():
            self._set_table_field(c, field, value)

        # Seller Info
        c.seller = self.parse_seller_info()
        c.images = self.parse_images()
        c.scraped_at = datetime.now().isoformat()

        return c


# Utility methods
def parse_search_results(search_url):
    car_ids = SearchResultPageParser(search_url).parse()
    for car_id in car_ids:
        yield parse_car_page(car_id)


def parse_car_page(car_id):
    car = CarItemParser(car_id).parse()
    return car
