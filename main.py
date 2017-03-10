#!python3
#encoding:utf-8
import xmltodict
from collections import OrderedDict
from requests_oauthlib import OAuth1Session
from bs4 import BeautifulSoup
import datetime
import xml.sax.saxutils
import html
import dataset
from urllib.parse import urlparse
import re

class Scraping(object):
    def __init__(self, 
                path_service_xml, 
                path_hatena_accounts_sqlite3, 
                path_hatena_blogs_sqlite3,
                path_hatena_entries_sqlite3):
        self.soup = BeautifulSoup(self.__load_file(path_service_xml), 'lxml')
        self.db_accounts = dataset.connect('sqlite:///' + path_hatena_accounts_sqlite3)
        self.db_blogs = dataset.connect('sqlite:///' + path_hatena_blogs_sqlite3)
        self.db_entries = dataset.connect('sqlite:///' + path_hatena_entries_sqlite3)
        self.blog_id = self.__get_blog_id(path_hatena_entries_sqlite3)
        print(self.blog_id)
        self.hatena_blog_id = self.__get_hatena_blog_id(self.blog_id)
        self.hatena_id = self.__get_hatena_id(self.blog_id)
        print(self.hatena_id)
        
    def scrape(self):
        self.db_entries.begin()
        for entry in self.soup.find_all('entry'):
            self.__parse_to_entry_info(entry)
        self.db_entries.end()
            
    def __load_file(self, file_name, encoding='utf-8'):
        with open(file_name, mode='r', encoding=encoding) as f:
            return f.read()

    def __get_blog_id(self, path_hatena_entries_sqlite3):
#        return re.sub(r'.sqlite3', "", re.sub(r'Hatena.Blog.Entries.', "", path_hatena_entries_sqlite3))
        return re.sub(r'.sqlite3', "", re.sub(r'meta_Hatena.Blog.Entries.', "", path_hatena_entries_sqlite3))

    def __get_hatena_blog_id(self, blog_id):
        return self.db_blogs['Blogs'].find_one(BlogId=blog_id)['HatenaBlogId']

    def __get_hatena_id(self, blog_id):
        account_id = self.db_blogs['Blogs'].find_one(BlogId=blog_id)['AccountId']
        return self.db_accounts['Accounts'].find_one(Id=account_id)['HatenaId']

    def __parse_to_entry_info(self, entry):
        entry_id = self.__get_entry_id(entry)
        print("entry_id="+entry_id)
        
        if (None == self.db_entries['Entries'].find_one(EntryId=entry_id)):
            self.db_entries['Entries'].insert(dict(
                EntryId=entry_id,
                Url=entry.find('link', rel='alternate').get('href'),
                Title=entry.find('title').string,
                Summary=entry.find('summary').string,
                ContentType=entry.find('content').get('type'),
                Content=html.unescape(entry.find('content').string),
                HtmlContent=html.unescape(entry.find('hatena:formatted-content', type='text/html').string),
                Categories=self.__get_category(entry),
                IsDraft=self.__get_draft(entry),
                Edited=entry.find('app:edited').string,
                Published=entry.find('published').string,
                Updated=entry.find('updated').string
            ))
            print(self.db_entries['Entries'].find_one(EntryId=entry_id))
        else:
            print('{0}のレコードはすでに存在している。'.format(entry_id))
            print(self.db_entries['Entries'].find_one(EntryId=entry_id))

    def __get_entry_id(self, entry):
        entry_id = re.sub(r'tag:blog.hatena.ne.jp,[0-9]+:', "", entry.find('id').string)
        return entry_id.replace("blog-{0}-{1}-".format(self.hatena_id, self.hatena_blog_id), "")
        
    def __get_category(self, entry):
        categories = ""
        for cate in entry.find_all('category'):
            categories = cate.get('term') + ','
        categories = categories[:-1]

    def __get_draft(self, entry):
        draft = entry.find('app:control').find('app:draft').string.lower()
        if ('yes' == draft):
            return 1
        elif ('no' == draft):
            return 0
        else:
            raise Exception('app:draftの値が想定外。:' + draft)
        
if __name__ == '__main__':
    client = Scraping(
        "../resource/201702281505/ytyaru.ytyaru.hatenablog.com.Services.xml", 
        "meta_Hatena.Accounts.sqlite3",
        "meta_Hatena.Blogs.sqlite3",
        "meta_Hatena.Blog.Entries.ytyaru.hatenablog.com.sqlite3")
    client.scrape()

