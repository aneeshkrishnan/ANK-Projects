'''
Created on 15-Aug-2018

@author: V.Supriya
'''
import os
import json
import http.client, urllib.parse,json
import pymongo
import sys
import re
import traceback
from _collections import defaultdict
import requests

uri = "mongodb://acemwpdbpacdb01:3bomhjlK16WD9tDKUAGFd62KKfHXcPoMM7UDbtqIgeXmkgUymTboLX74mV9RlPlvZGlce1zeiikzX2XeLlAokw==@acemwpdbpacdb01.documents.azure.com:10255/?ssl=true&replicaSet=globaldb"
client = pymongo.MongoClient(uri)
language = "en-us"
#language = "en-GB"
database=client.get_database('BPADB')
collection=database.get_collection('FileContent')
#data=collection.find_one({"DocumentID": "5b6d87ad9a762129d073a2a5"})#6
data=collection.find_one({"DocumentID": "5b6c49f3e670fa23e8d76c6e"}) #412
#data=collection.find_one({"DocumentID": "5b714bcb9a762129d073a2e0"})#11
pages=data['Content']['pages']


def index_idetifier(txt,tkn,a_idx):
    for i in re.finditer(re.sub('\W','\W',tkn),txt[a_idx:]):
        start_value=a_idx+i.start(0)
        end_value=a_idx+i.end(0)
        return((start_value,end_value))

def extractNER(doc_id):
    result = defaultdict(set)
    ner_url = "https://acemwsdbpaweb01.azurewebsites.net/BluePencilNERService-0.1.2/entities"
    querystring = {"documentId": doc_id, "ner": "all"}
    try :       
        response = requests.request("GET", ner_url, params=querystring).json()
        if 'message' in response and response['message'] == "Success":
            #result += {entity['entity'].split('\n')[0].strip().lower():entity['source']
            #print(response['entities'])
            for page in response['entities']:
                for entity in page['entities']:
                    if entity['type'] == 'ORG' or entity['type'] == 'LOC':
                        v="1" if entity['source'] == "Azure" else "2"
                        result[entity['entity']].add(1 if entity['source'] == "Azure" else 2)
    except Exception as e:
        print("NER error")
        print(e)
        traceback.print_exc()
    return result

def getMatch(val,start,end,allWebMatches):    
    for each in allWebMatches:
        webVal=each.group(0)
        webStart=each.start()
        webEnd = each.end()
        if val == webVal or (webStart <= start and webEnd >=end):
            return True
    return False

def text_concatenete():
    all_text=""
    page_list=[]
    each_page_length=0
    for page in pages:
        page_text=page['text']
        page_text = page_text+" "
        each_page_length += len(page_text)
        all_text += page_text
        page_list.append(each_page_length)
    return all_text,page_list



def SpellCheck_engine(text,idx,pageList,nerKeys):
    data = {'text': re.sub(r'[\n\r\s]+'," ",text)}
    allwebaddressRegex = r"\b([^\s]{2,256}\.[a-z\!]{2,6}\b([^\s]*))|([^\s]+[@][^\s]+[.][^\s]{2,})"
    allWebMatches = re.finditer(allwebaddressRegex, text)
    allWebMatches = list(allWebMatches)
    processed_data={}
    key ='0b1b398f43df4bf197c23bb4b732f904'
    host = 'api.cognitive.microsoft.com'
    path = '/bing/v7.0/spellcheck?'
    params = 'mkt={0}&mode=proof'.format(language)
    headers = {'Ocp-Apim-Subscription-Key': key,
    'Content-Type': 'application/x-www-form-urlencoded'}
    try:
        conn = http.client.HTTPSConnection(host)
        body = urllib.parse.urlencode (data)
        conn.request ("POST", path + params, body, headers)
        response = conn.getresponse ()
        output = json.loads(response.read())
        annotation_list=[]
        if output['flaggedTokens']:
            for tkn_sugg in output['flaggedTokens']:
                
                txt_idx=index_idetifier(text,tkn_sugg['token'],tkn_sugg['offset'])
                if txt_idx and tkn_sugg['token'] not in nerKeys: #or (tkn_sugg['token'] in nerKeys and len(nerResult[tkn_sugg['token']]) <2)):
                    matchFlag=getMatch(tkn_sugg['token'],txt_idx[0],txt_idx[1],allWebMatches)
                    if matchFlag:
                        continue
                    annotation = {
                            "Regex":"-1",
                            "Start":txt_idx[0]+idx,
                            "End":txt_idx[1]+idx,
                            "PageNo":next(i+1 for i,v in enumerate(pageList) if v > txt_idx[1]+idx),
                            "Format":"-1",
                            "Color":"yellow",
                            "Text":text[txt_idx[0]:txt_idx[1]],
                            "Message":'This word is repeated. Please avoid if possible.' if tkn_sugg['type'] ==  'RepeatedToken' else ('Suggestions: ' + ', '.join([x['suggestion'] for x in tkn_sugg['suggestions']])),
                            "Type":"IP"
                        }
                    annotation_list.append(annotation)
    except Exception as e:
        print("Bing Error: ",e)
        traceback.print_exc()
    return annotation_list

def spell_check():
    
    nerResult = extractNER("5b6c4a1be670fa23e8d76c6f")
    nerKeys = nerResult.keys()
    print("NER kays: ",nerKeys)
    txt_result=[]
    data=text_concatenete()
    all_text=data[0]
    page_list=data[1]
    i = 0
    while i< len(all_text):
        if i+10000 <= len(all_text):
            text = all_text[i:i+10000]
            text = text[:text.rfind(" ")]
            txt_result.extend(SpellCheck_engine(text,i,page_list,nerKeys))
            i += len(text)+1
        else:
            text = all_text[i:]
            txt_result.extend(SpellCheck_engine(text,i,page_list,nerKeys))
            break
    return txt_result


print(spell_check())