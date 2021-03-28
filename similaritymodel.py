# -*- coding: utf-8 -*-
"""SimilarityModel.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/102j1wvFjnumazoa4RcXuN7nw30ClKXH7

Installing transformers library
"""

from google.colab import drive
drive.mount('/content/drive')

!pip install transformers

"""Importing dependencies"""

import torch
import random
import numpy as np
import pandas as pd
import torch.nn as nn
import torch.optim as optim
from tqdm.notebook import tqdm
import torch.nn.functional as F
from torchvision import transforms
from transformers import AutoTokenizer, AutoModel

"""Network class defines the architecture and forward propagation of the model used to fine tune and create meaninful sentence embeddings from the pretrained word embeddings model, using PyTorch."""

class Network(nn.Module):
  
  def __init__(self, input_size, hidden_size, num_layers):
    
    super(Network, self).__init__()
    self.input_size = input_size
    self.hidden_size = hidden_size
    self.num_layers = num_layers
    self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first = True, bidirectional = True)
    self.fc = nn.Linear(hidden_size*2, hidden_size*2)
        
  def forward_once(self, x, length):

    x = nn.utils.rnn.pack_padded_sequence(x, length, batch_first=True)
    x, (hidden, cell) = self.lstm(x)
    x = torch.cat((hidden[-2,:,:], hidden[-1,:,:]), dim = 1)
    x = self.fc(x)
    return x
    
  def forward(self, input1, length1, input2, length2):

    output1 = self.forward_once(input1, length1)
    output2 = self.forward_once(input2, length2)
    return output1, output2

"""Checking for availability of GPU"""

device = 'cuda' if torch.cuda.is_available() else 'cpu'

"""Loading the pretrained word embeddings model.

Link to pretrained model: https://huggingface.co/gsarti/biobert-nli?text=The+goal+of+life+is+%5BMASK%5D.
"""

tokenizer = AutoTokenizer.from_pretrained("gsarti/biobert-nli")
model = AutoModel.from_pretrained("gsarti/biobert-nli",output_hidden_states=True)
model.to(device)
model.eval()

"""Setting the parameters of the Network class"""

input_size = 768
sequence_length = 512
num_layers = 2
hidden_size = 768

"""Loading the trained fine tuning model to extract sentence embeddings."""

SimilarityModel = Network(input_size, hidden_size, num_layers)
SimilarityModel.load_state_dict(torch.load("drive/My Drive/SimilarityModel.pt")) #Replace path with path of trained model file
SimilarityModel = SimilarityModel.to(device)
SimilarityModel.eval()

"""Loading the database of Question Answer pairs, and creating a list of questions and answers separately."""

db = pd.read_csv("db.csv", encoding="cp1252")#Replace path with bath of data file(csv, having 2 columns: Question and Answer respectively) 
db.columns = ["Question", "Answer"]
question_list = []
answer_list = []
for index, row in db.iterrows():
  question_list.append(row["Question"])
  answer_list.append(row["Answer"])

"""Utility function that returns the word embeddings, for a string passed as input, extracted from the pretrained word embeddings model."""

def get_word_embeddings(Question):

  sentence_token_ids = tokenizer.encode(Question)
  sentence_token_ids = torch.LongTensor(sentence_token_ids).unsqueeze(0)
  sentence_token_ids = sentence_token_ids.to(device)
  with torch.no_grad():
    word_embeddings = (model(input_ids=sentence_token_ids)[2])[-1]
  return word_embeddings

"""Utility function that calls the get_word_embeddings function, generates sentence embeddings for both input strings (Q1 and Q2) by passing the word embeddings for each of them to the similarity model(defined in Network class) and finally returns the pairwise eucledian distance between the generated sentence embeddings."""

def get_difference(Q1, Q2):
  
  embedding_Q1 = (get_word_embeddings(Q1)).to(device)
  embedding_Q2 = (get_word_embeddings(Q2)).to(device)
  embedding_Q1, embedding_Q2 = SimilarityModel(embedding_Q1, torch.tensor([embedding_Q1.shape[1]]), embedding_Q2, torch.tensor([embedding_Q2.shape[1]]))
  difference = F.pairwise_distance(embedding_Q1, embedding_Q2)
  return difference

"""Takes as input the new query and returns the confidence level(0/1), the question with the closest semantic relationship(according to the similarity model) with the input query(from the database) and the answer to the question(from the database)."""

def get_best_match(Question):
  differences = []
  for question in question_list:
    differences.append(get_difference(question, Question))
  min_index = differences.index(min(differences))
  if differences[min_index] > 0.8 :
    confidence = 0
  else :
    confidence = 1
  return confidence, question_list[min_index], answer_list[min_index]

"""Driver code to demostrate working of the model."""

confidence, question, answer = get_best_match("What are the symptoms of corona virus?")
print(confidence)
print(question)
print(answer)