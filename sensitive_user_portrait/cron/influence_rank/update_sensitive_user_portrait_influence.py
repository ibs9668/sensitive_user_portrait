# -*- coding: utf-8 -*-
"""
copy es_portrait to a new es, for the use of record user_index

"""

import sys
import time
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan

reload(sys)
sys.path.append('./../../')
from global_utils import ES_CLUSTER_FLOW1, es_user_profile

es = ES_CLUSTER_FLOW1
copy_sensitive_user_portrait = "copy_sensitive_user_portrait" # act as portrait database
user_portrait_doctype = "user"
index_destination = '20130907'
index_destination_doctype = "bci"

def expand_index_action(data):
    _id = data['uid']
    action = {'index': {'_id': _id}}
    return action, data

def co_search(es, user_list, bulk_action, count_n, tb):
    search_list = []
    for item in user_list:
        uid = item.get('uid', '0') # obtain uid, notice "uid" or "user"
        search_list.append(uid)

    search_result = es.mget(index=index_destination, doc_type=index_destination_doctype, body={"ids": search_list}, _source=True)["docs"]
    search_list = []

    for i in range(len(search_result)):
        item = search_result[i]
        source_dict = user_list[i]
        if not item['found']:
            source_dict.update({index_destination: 0})
        else:
            source_dict.update({index_destination: item['_source']['user_index']})
        xdata = expand_index_action(source_dict)
        bulk_action.extend([xdata[0], xdata[1]])
        count_n += 1
        if count_n % 1000 == 0:
            es.bulk(bulk_action, index=copy_sensitive_user_portrait, doc_type=user_portrait_doctype, timeout=30)
            bulk_action = []
            print count_n

        if count_n % 10000 == 0:
            ts = time.time()
            print "count_n %s  per  %s  second"  %(count_n, ts-tb)
            print "count %s " % count
            tb = ts

    return bulk_action, count_n, tb

if __name__ == "__main__":

    tb = time.time()
    es = ES_CLUSTER_FLOW1

    index_exist = es.indices.exists(index=index_destination)
    if not index_exist:
        es.indices.create(index=index_destination, ignore=400)

    s_re = scan(es, query={"query":{"match_all":{}},"size":1000}, index=copy_sensitive_user_portrait, doc_type=user_portrait_doctype)
    bulk_action = []
    count = 0
    count_n = 0
    search_list = []
    user_list = []
    while 1:
        try:
            scan_re = s_re.next()['_source']
            count += 1
            user_list.append(scan_re)
            if count % 1000 == 0:
                bulk_action, count_n, tb = co_search(es, user_list, bulk_action, count_n, tb)
                user_list = []
        except StopIteration:
            print "all done"
            bulk_action, count_n, tb = co_search(es, user_list, bulk_action, count_n,tb)
            break
        except Exception, r:
            print Exception, r
            sys.exit(0)


    if bulk_action:
        es.bulk(bulk_action, index=index_destination, doc_type=index_destination_doctype, timeout=30)

    print count
    print count_n

