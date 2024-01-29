# AUTOGENERATED! DO NOT EDIT! File to edit: 240117_MC_Text_App_3.ipynb.

# %% auto 0
__all__ = []

# %% 240117_MC_Text_App_3.ipynb 1
import pandas as pd
import pickle
import numpy as np
import string
# from datasets import Dataset
# from transformers import AutoTokenizer, TFAutoModel
import nltk
import collections
from collections import Counter
import re

from itables import init_notebook_mode

init_notebook_mode(all_interactive=True)

from datetime import datetime
import streamlit as st
from streamlit_jupyter import StreamlitPatcher, tqdm
# from st_aggrid import AgGrid

# from yaspin import yaspin
# from yaspin.spinners import Spinners

sp = StreamlitPatcher()
sp.jupyter()

# %% 240117_MC_Text_App_3.ipynb 2
st.title("Palestine Media Observer - WIP (Do Not Distribute)")
st.write("All enquiries to pmo[at]commonspring.maskmy.id")


# %% 240117_MC_Text_App_3.ipynb 3
@st.cache_data
def load_articles():
    df = pd.read_parquet("https://github.com/commonspring/pmo/blob/a17b00272b47811562deebabdf3d2f0e03bb99c9/data/mc_us_national_articles_text_0103.parquet")[['id', 'media_name', 'publish_date', 'title', 'article_url',
       'media_type', 'partisan', 'broad_partisan', 'text']]
    return df

@st.cache_data
def load_sentences():
    df = pd.read_csv("https://github.com/commonspring/pmo/blob/a17b00272b47811562deebabdf3d2f0e03bb99c9/data/mc_us_national_sentences_filtered_0112.parquet")
    return df

with st.spinner(text='Loading data...'):
    mc_articles = load_articles()
    mc_articles["partisan"] = mc_articles["partisan"].astype("category").cat.set_categories(["left", "center left", "center", "center right", "right"], ordered=True)
    mc_articles["broad_partisan"] = mc_articles["broad_partisan"].astype("category").cat.set_categories(["broadly left", "center", "broadly right"], ordered=True)
    mc_articles["text_snippet"] = mc_articles["text"].apply(lambda x: x[:200])
    # mc_features = mc_subset[["id", "publish_date", "title", "article_url", "media_name", "pub_state", "partisan", "broad_partisan"]].copy(deep=True)

    # Load text data
    mc_sents = load_sentences()
    # Add sent split
    mc_sents["sent_split"] = [x.split(" ") for x in mc_sents["sent"]]
    # Add index
    mc_sents["sent_id"] = range(len(mc_sents))
    # Order categories
    # set and order categories
    mc_sents["partisan"] = mc_sents["partisan"].astype("category").cat.set_categories(["left", "center left", "center", "center right", "right"], ordered=True)
    mc_sents["broad_partisan"] = mc_sents["broad_partisan"].astype("category").cat.set_categories(["broadly left", "center", "broadly right"], ordered=True)


# %% 240117_MC_Text_App_3.ipynb 4
st.subheader(
    """

Articles dataset overview

"""
)

# %% 240117_MC_Text_App_3.ipynb 5
# Number of articles by partisan
art_ct = {}
for partisan_col in ["partisan", "broad_partisan"]:
    
    art_ct[partisan_col] = mc_articles.groupby(partisan_col, observed=False)\
            .agg(**{\
            f"total_articles": pd.NamedAgg(column=f"article_url", aggfunc="nunique"),
            f"total_sources": pd.NamedAgg(column=f"media_name", aggfunc="nunique"),
            });
    
# Number of sources by partisan
source_partisan_dict = {}
for partisan_col in ["partisan", "broad_partisan"]:
    source_to_partisan = mc_articles[["media_name", partisan_col]].drop_duplicates()
    source_partisan_dict[partisan_col] = dict(zip(source_to_partisan["media_name"], source_to_partisan[partisan_col]))

# Top sources
sources_count = mc_articles.drop_duplicates(subset=["article_url"])
sources_count = sources_count["media_name"].value_counts()[:200].to_frame("num_articles_by_source")
sources_count["partisan"] = sources_count.index.map(source_partisan_dict["partisan"])
sources_count["partisan"] = sources_count["partisan"].fillna("")



# %% 240117_MC_Text_App_3.ipynb 6
st.write(sources_count[:50])
st.write(art_ct["partisan"])
st.write(art_ct["broad_partisan"])

# %% 240117_MC_Text_App_3.ipynb 8
st.subheader(
    """

Exact search within articles

"""
)

# %% 240117_MC_Text_App_3.ipynb 12
# Total articles by partisan group
art_ct = {}
for partisan_col in ["partisan", "broad_partisan"]:
    
    art_ct[partisan_col] = mc_articles.groupby(partisan_col, observed=False)\
            .agg(**{\
            f"total_articles": pd.NamedAgg(column=f"article_url", aggfunc="nunique"),
            f"total_sources": pd.NamedAgg(column=f"media_name", aggfunc="nunique"),
            });
    
def get_articles_from_query(query, partisan_col):
    
    mc_features = mc_articles[["article_url", "media_name", "partisan", "broad_partisan"]].copy()
    # mc_features = mc_articles[["article_url", "media_name", "partisan", "broad_partisan"]].copy().sample(50, random_state = 3)

    if "AND" in query:
        query_list = [word.strip().lower() for word in query.split("AND")]
        pattern = ""
        for word in query_list:
            pattern += fr'(?=.*{word})'


    elif "OR" in query:
        query_list = [word.strip().lower() for word in query.split("OR")]
        pattern = r"|".join(query_list)

    elif len(query)>0:
        query = query.strip().lower()
        pattern = fr"\b{query}"

    else:
        print("ERROR: query is invalid")
        return

    # print(pattern)
    # Count mentions and occurences per sentence
    mc_features["did_article_mention_query"] = mc_articles["text"].str.contains(pattern, regex=True)
    # mc_features["num_occurences_query"] = mc_articles["sent"].str.count(pattern)

    # Filter only for articles that mention query
    mc_features = mc_features.loc[mc_features[f"did_article_mention_query"]].copy()

    return mc_features

def get_sample_articles_from_query(query, partisan_col):
    mc_features = get_articles_from_query(query, partisan_col)
    mc_subset = mc_articles.loc[mc_articles["article_url"].isin(mc_features["article_url"]), ['publish_date', 'article_url', 'media_name', 'text_snippet', partisan_col]].copy()
    return mc_subset.sample(frac=1)[:200].sort_values("publish_date", ascending=False)

def get_top_sources_from_query(query, partisan_col):
    mc_features = get_articles_from_query(query, partisan_col)
    mc_articles = mc_features[["media_name", "article_url"]].drop_duplicates()
    mc_articles = mc_articles["media_name"].value_counts()[:20].to_frame("num_articles_by_source")
    mc_articles[partisan_col] = mc_articles.index.map(source_partisan_dict[partisan_col])
    return mc_articles

def get_grouped_counts_from_query(query, partisan_col):

    mc_features = get_articles_from_query(query, partisan_col)

    # Break if no match
    if len(mc_features) == 0:
        st.write("No matches found")
        return pd.DataFrame()

    # Created grouped counts for each partisan group
    grouped_count = mc_features.groupby(partisan_col, observed=False).agg(**{\
        f"num_articles_mention_query": pd.NamedAgg(column=f"article_url", aggfunc="nunique"),
        f"num_sources_mention_query": pd.NamedAgg(column=f"media_name", aggfunc="nunique"),
        });
    grouped_count = grouped_count.join(art_ct[partisan_col])

    # Sum for all partisan groups
    grouped_count.loc['all',:] = grouped_count.sum(axis=0)

    # Pct mentions
    grouped_count["pct_articles_mention_query"] = grouped_count[f"num_articles_mention_query"]*100/grouped_count[f"total_articles"]
    grouped_count["pct_sources_mention_query"] = grouped_count[f"num_sources_mention_query"]*100/grouped_count[f"total_sources"]

    grouped_count = np.round(grouped_count)

    # Articles count
    articles_count = grouped_count[["num_articles_mention_query", "total_articles", "pct_articles_mention_query"]]

    # Sources count
    sources_count = grouped_count[["num_sources_mention_query", "total_sources", "pct_sources_mention_query"]]

    return articles_count, sources_count

def get_ratio_article_counts_words(query1, query2, partisan_col):
    df1 = get_grouped_counts_from_query(query1, partisan_col)[0].rename(columns={"num_articles_mention_query": "num_articles_mention_query1"})
    df2 = get_grouped_counts_from_query(query2, partisan_col)[0].rename(columns={"num_articles_mention_query": "num_articles_mention_query2"})
    ratio_df = df1[f"num_articles_mention_query1"]/df2[f"num_articles_mention_query2"]
    ratio_df = ratio_df.to_frame(name=f"total_count_ratio")
    return np.round(ratio_df,2)              

# %% 240117_MC_Text_App_3.ipynb 14
po1 = "broadly left, center, broadly right"
po2 = "left, center left, center, center right, right"

partisan_option = st.selectbox("Select media partisan labels to compare: ", options=[po1, po2], index=0)

partisan_option_dict = {po1: "broad_partisan", po2: "partisan"}

partisan_col = partisan_option_dict[partisan_option]

# %% 240117_MC_Text_App_3.ipynb 15
st.write('You selected:', partisan_option)

# %% 240117_MC_Text_App_3.ipynb 16
query = st.text_input("Find articles containing exact match to this query...", "hamas AND gaza")

# %% 240117_MC_Text_App_3.ipynb 17
with st.spinner(text='In progress'):
    try:
    
        st.markdown('_Count of articles mentioning your query_')
        query_counts = get_grouped_counts_from_query(query, partisan_col)[0]

        st.write(query_counts)

        st.markdown('_Top media sources mentioning your query_')
        top_sources = get_top_sources_from_query(query, partisan_col)

        st.write(top_sources)

        st.markdown('_Sample of setence snippets for your query_')
        samp_sentences = get_sample_articles_from_query(query, partisan_col)

        st.write(samp_sentences)
    except Exception as e:
        st.write("Error with your query.")

# %% 240117_MC_Text_App_3.ipynb 18
st.subheader(
    """

Ratio of mentions within articles

"""
)

# %% 240117_MC_Text_App_3.ipynb 19
word1 = st.text_input("Compare articles mentioning this term...", "hamas")
word2 = st.text_input("...to articles mentioning this term", "palestin")

# %% 240117_MC_Text_App_3.ipynb 20
ratio_table = get_ratio_article_counts_words(word1, word2, partisan_col)
st.write(ratio_table)

# %% 240117_MC_Text_App_3.ipynb 21
st.subheader(
    """

Find most common words after...

"""
)

# %% 240117_MC_Text_App_3.ipynb 22
# lemma = nltk.SnowballStemmer("english")
lemma = nltk.wordnet.WordNetLemmatizer()

en_stopwords = ['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 
'ourselves', 'you', "you're", "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 
'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers', 'herself', 
'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are',
 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing',
 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 
'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 
'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 
'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 
'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 
's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y',
 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 
'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn',
 "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 
'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"]

stop_words = set(en_stopwords)

def find_words_after(word, text_list):
    word = word.strip().lower()

    # "tokenize" by splitting on " "
    text_split = [ x.split(" ") for x in text_list ]

    p_ind = [[n for n, w in enumerate(text) if w == word] for text in text_split ]
    max_ind = [len(text) for text in text_split ]

    p_ind_after = [[n+1 for n in ind if n+1 < mi] for ind,mi  in zip(p_ind, max_ind)]

    p_word_after = [[text[x] for x in indexes] for indexes,text in zip(p_ind_after,text_split )]
    p_word_after_flat = [item for sublist in p_word_after for item in sublist]

    # top_words_df = pd.DataFrame(word_counts.most_common(500), columns=["Word", "Count"])
    return p_word_after_flat

def clean_word_list(word_list):
    # Strip punctuation
    wl = [re.sub(r'[^\w\s]', '', w) for w in word_list]
    # Remove stopwords
    wl = [w for w in wl if not w.lower() in stop_words]
    # Lemmatize words
    # wl = [lemma.stem(w) for w in wl]
    wl = [lemma.lemmatize(w) for w in wl]
    return wl

def get_top_words_after(word, text_list, N):
    wl = find_words_after(word, text_list)
    cl = clean_word_list(wl)
    # Count words
    word_counts = Counter(cl)
    top_words_df = pd.DataFrame(word_counts.most_common(N), columns=["Word", "Count"])
    
    return top_words_df

def get_top_words_combine(word_list, text_list, N):
    out_list = []
    for w in word_list:
        o = get_top_words_after(word, text_list)
        o = o.set_index("Word")
        out_list.append(o)
    out_df = pd.concat(out_list, axis=1)
    out_df["Total Count"] = out_df.sum(axis=1)
    out_df = out_df[["Total Count"]].reset_index()
    return out_df
    
        

# %% 240117_MC_Text_App_3.ipynb 23
anchor_word = st.text_input("Find most common words after...", "palestinian")

# %% 240117_MC_Text_App_3.ipynb 24
# with yaspin(Spinners.aesthetic, text="Calculating...") as sp:
with st.spinner(text='In progress'):
    out = get_top_words_after(anchor_word, mc_sents["sent"], 50)
    st.write(out)
