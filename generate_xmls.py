import json
import os
import pandas as pd
from feedgen.feed import FeedGenerator
from tqdm import tqdm

from src.gpt_utils import generate_chatgpt_summary
from src.config import TOKENIZER


class GenerateXML:
    def __init__(self) -> None:
        pass

    def check_size_body(self, body):
        tokens = TOKENIZER.encode(body)
        temp = len(tokens) // 3000 + 1 if len(tokens) % 3000 else 0
        bodies = []
        sub_body_size = len(body) // temp
        for i in range(temp):
            s_num = sub_body_size * i
            e_num = (sub_body_size * i) + sub_body_size
            bodies.append(body[s_num:e_num])
        return bodies

    def gpt_api(self, body):
        summ = []
        for b in self.check_size_body(body):
            summ.append(generate_chatgpt_summary(b))
        return "\n".join(summ)

    def create_summary(self, body):
        summ = self.gpt_api(body)
        return summ

    def create_folder(self, month_year):
        os.makedirs(month_year)

    def generate_xml(self, feed_data, xml_file):
        # create feed generator
        fg = FeedGenerator()
        fg.id(feed_data['id'])
        fg.title(feed_data['title'])
        for author in feed_data['authors']:
            fg.author({'name': author})
        fg.link(href=feed_data['base_url'], rel='alternate')
        # add entries to the feed
        fe = fg.add_entry()
        fe.id(feed_data['url'])
        fe.title(feed_data['title'])
        fe.link(href=feed_data['url'], rel='alternate')
        fe.published(feed_data['created_at'])
        fe.summary(feed_data['summary'])

        # generate the feed XML
        feed_xml = fg.atom_str(pretty=True)
        # convert the feed to an XML string
        # write the XML string to a file
        with open(xml_file, 'wb') as f:
            f.write(feed_xml)

    def start(self, json_path):
        data = open(json_path, "r")
        dict_data = []
        for line in data:
            dict_data.append(json.loads(line))

        columns = ['_index', '_id', '_score']
        source_cols = ['body_type', 'created_at', 'id', 'title', 'body', 'type',
                       'url', 'authors']
        df_list = []
        for i in range(len(dict_data)):
            df_dict = {}
            for col in columns:
                df_dict[col] = dict_data[i][col]
            for col in source_cols:
                df_dict[col] = dict_data[i]['_source'][col]
            df_list.append(df_dict)
        emails_df = pd.DataFrame(df_list)

        emails_df['created_at_org'] = emails_df['created_at']
        emails_df['created_at'] = pd.to_datetime(emails_df['created_at'], format="%Y-%m-%dT%H:%M:%S.%fZ")
        result = emails_df.groupby([emails_df['created_at'].dt.month, emails_df['created_at'].dt.year])

        for month_year, email_df in tqdm(result):
            str_month_year = f"{month_year[1]}_{month_year[0]}"
            if not os.path.exists(f"static/{str_month_year}"):
                self.create_folder(f"static/{str_month_year}")
            for i in email_df.index:
                number = str(email_df.loc[i]['id']).split("-")[-1]
                special_characters = ['/', ':', '@', '#', '$', '*', '&', '<', '>', '\\']
                xml_name = email_df.loc[i]['title']
                for sc in special_characters:
                    xml_name = xml_name.replace(sc, "-")
                print(xml_name)
                file_path = f"static/{str_month_year}/{number}_{xml_name}.xml"
                if os.path.exists(file_path):
                    continue
                summary = self.create_summary(email_df.loc[i]['body'])
                feed_data = {
                    'id': email_df.loc[i]['id'],
                    'title': email_df.loc[i]['title'],
                    'base_url': email_df.loc[i]['url'],
                    'authors': email_df.loc[i]['authors'],
                    'url': email_df.loc[i]['url'],
                    'created_at': email_df.loc[i]['created_at_org'],
                    'summary': summary
                }

                self.generate_xml(feed_data, file_path)


if __name__ == "__main__":
    gen = GenerateXML()
    json_path = "./data/bitcoin-search-index-revamped.json"
    gen.start(json_path)
