#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
from keras.models import Sequential
from keras.layers.core import Dense, Activation, Dropout
from keras.layers.recurrent import LSTM
from keras.datasets.data_utils import get_file
from sylabledivider import SyllableDivider
from keras.models import model_from_json
import numpy as np
import random
import sys

def RepresentsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

'''
    At least 20 epochs are required before the generated text
    starts sounding coherent.

    It is recommended to run this script on GPU, as recurrent
    networks are quite computationally intensive.

    If you try this script on new data, make sure your corpus
    has at least ~100k characters. ~1M is better.
'''

if len(sys.argv) != 2:
   print('need filename to read')
   sys.exit()

path = sys.argv[1]
input_text = open(path).read().replace('\n', ' ').lower()
print('corpus length:', len(input_text))

words = input_text.split(' ')
syllables = []
for word in words:
    word_without_special_chars = word.translate(str.maketrans('', '', '.\"\',!;\-:”„?()é[]'))
    word_syllables = word_without_special_chars
    if not RepresentsInt(word_without_special_chars):
        word_syllables = SyllableDivider(word_without_special_chars).divide()
    syllables.extend(word_syllables)
    syllables.append(' ')

input_text = syllables
char_set = set(syllables)

#char_set = set(input_text)
print('total char set length:', len(char_set))
char_indices = dict((c, i) for i, c in enumerate(char_set))
indices_char = dict((i, c) for i, c in enumerate(char_set))

# cut the text in semi-redundant sequences of maxlen characters
sequence_maxlen = 10
sequence_step = 5


def create_training_data(input_text, sequence_length, step):
    sequences = []
    next_chars = []
    for i in range(0, len(input_text) - sequence_length, step):
        sequences.append(input_text[i: i + sequence_length])
        next_chars.append(input_text[i + sequence_length])
    return sequences, next_chars


sequences, next_chars = create_training_data(input_text, sequence_length=sequence_maxlen, step=sequence_step)
print('nb sequences:', len(sequences))

print('Vectorization...')
X = np.zeros((len(sequences), sequence_maxlen, len(char_set)), dtype=np.bool)
y = np.zeros((len(sequences), len(char_set)), dtype=np.bool)
for i, sentence in enumerate(sequences):
    for t, char in enumerate(sentence):
        X[i, t, char_indices[char]] = 1
    y[i, char_indices[next_chars[i]]] = 1


# build the model: 2 stacked LSTM
print('Build model...')
if 	os.path.isfile('my_model_architecture_sylabes.json'):
	model = model_from_json(open('my_model_architecture_sylabes.json').read())
	if os.path.isfile('my_model_weights_sylabes.h5'):
		model.load_weights('my_model_weights_sylabes.h5')
else:
	model = Sequential()
	model.add(LSTM(512, return_sequences=True, input_shape=(sequence_maxlen, len(char_set))))
	model.add(Dropout(0.2))
	model.add(LSTM(512, return_sequences=False))
	model.add(Dropout(0.2))
	model.add(Dense(len(char_set)))
	model.add(Activation('softmax'))

model.compile(loss='categorical_crossentropy', optimizer='rmsprop')


def sample(a, temperature=1.0):
    # helper function to sample an index from a probability array
    a = np.log(a) / temperature
    a = np.exp(a) / np.sum(np.exp(a))
    return np.argmax(np.random.multinomial(1, a, 1))

def get_random_start_index(input_text, sequence_maxlen):
    return random.randint(0, len(input_text) - sequence_maxlen - 1)

# train the model, output generated text after each iteration
for iteration in range(1, 180):
    print()
    print('-' * 50)
    print('Iteration', iteration)
    model.fit(X, y, batch_size=128, nb_epoch=1)

    start_index = get_random_start_index(input_text, sequence_maxlen)

    for diversity in [0.2, 0.5, 1.0, 1.2]:
        print()
        print('----- diversity:', diversity)

        generated = ''
        sentence = input_text[start_index: start_index + sequence_maxlen]
        generated.join(sentence);
        print('----- Generating with seed: "' + ''.join(sentence) + '"')
        sys.stdout.write(generated)

        def prepare_generation_input_mat(sentence, sequence_maxlen, char_set):
            x = np.zeros((1, sequence_maxlen, len(char_set)))
            for t, char in enumerate(sentence):
                x[0, t, char_indices[char]] = 1.
            return x

        #Generate 400 characters
        for iteration in range(400):
            x = prepare_generation_input_mat(sentence, sequence_maxlen, char_set)

            preds = model.predict(x, verbose=0)[0]
            next_index = sample(preds, diversity)
            next_char = indices_char[next_index]

            generated += next_char
            #sentence = sentence[1:] + next_char
            sentence.pop(0)
            sentence.append(next_char)

            sys.stdout.write(next_char)
            sys.stdout.flush()
        print()

json_string = model.to_json()
open('my_model_architecture_sylabes.json', 'w').write(json_string)
model.save_weights('my_model_weights_sylabes.h5')
