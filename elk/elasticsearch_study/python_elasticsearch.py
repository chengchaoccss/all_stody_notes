from elasticsearch import Elasticsearch
from elasticsearch import AsyncElasticsearch
import pandas as pd
es = Elasticsearch(hosts="localhost",port=9200)

total = es.count(index="account")['count']
print(total)
query_json = {
    "query":{
        "match_all":{}
    },"size":2
}

data = es.search(index="account", body=query_json)
print(data["hits"]["hits"])
df = pd.DataFrame(data['hits']['hits'])
df = pd.DataFrame(list(df['_source']))
print(df)