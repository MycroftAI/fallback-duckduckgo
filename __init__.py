# Copyright 2017 Mycroft AI, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re
import sys
import requests

import ddg3 as ddg
from xml.etree import ElementTree
from adapt.intent import IntentBuilder

from mycroft.version import check_version
from mycroft.skills.common_query_skill import CommonQuerySkill, CQSMatchLevel
from mycroft.skills.skill_data import read_vocab_file
from mycroft import intent_handler


def split_sentences(text):
    """
    Turns a string of multiple sentences into a list of separate ones
    handling the edge case of names with initials
    As a side effect, .?! at the end of a sentence are removed
    """
    text = re.sub(r' ([^ .])\.', r' \1~.~', text)
    text = text.replace('Inc.', 'Inc~.~')
    for c in '!?':
        text = text.replace(c + ' ', '. ')
    sents = text.split('. ')
    sents = [i.replace('~.~', '.') for i in sents]
    if sents[-1][-1] in '.!?':
        sents[-1] = sents[-1][:-1]
    return sents

class DuckduckgoSkill(CommonQuerySkill):

    def __init__(self):
        super(DuckduckgoSkill, self).__init__()
        self.is_verb = ' is '
        self.in_word = 'in '
        # get ddg specific vocab for intent match
        fname = self.find_resource("DuckDuckGo.voc", res_dirname="locale")
        temp = read_vocab_file(fname)
        vocab = []
        for item in temp:
            vocab.append( " ".join(item) )
        self.sorted_vocab = sorted(vocab, key=lambda x: (-len(x), x))

        self.translated_question_words = self.translate_list("question_words")
        self.translated_question_verbs = self.translate_list("question_verbs")
        self.translated_articles = self.translate_list("articles")
        self.translated_start_words = self.translate_list("start_words")

    def format_related(self, abstract, query):
        self.log.debug('Original abstract: ' + abstract)
        ans = abstract

        if ans[-2:] == '..':
            while ans[-1] == '.':
                ans = ans[:-1]

            phrases = ans.split(', ')
            first = ', '.join(phrases[:-1])
            last = phrases[-1]
            if last.split()[0] in self.translated_start_words:
                ans = first
            last_word = ans.split(' ')[-1]
            while last_word in self.translated_start_words or last_word[-3:] == 'ing':
                ans = ans.replace(' ' + last_word, '')
                last_word = ans.split(' ')[-1]

        category = None
        match = re.search(r'\(([a-z ]+)\)', ans)
        if match:
            start, end = match.span(1)
            if start <= len(query) * 2:
                category = match.group(1)
                ans = ans.replace('(' + category + ')', '()')

        words = ans.split()
        for article in self.translated_articles:
            article = article.title()
            if article in words:
                index = words.index(article)
                if index <= 2 * len(query.split()):
                    name, desc = words[:index], words[index:]
                    desc[0] = desc[0].lower()
                    ans = ' '.join(name) + self.is_verb + ' '.join(desc)
                    break

        if category:
            ans = ans.replace('()', self.in_word + category)

        if ans[-1] not in '.?!':
            ans += '.'
        return ans

    def respond(self, query):
        if len(query) == 0:
            return 0.0

        # note: '1+1' throws an exception
        try:
            r = ddg.query(query)
        except Exception as e:
            self.log.warning("DDG exception %s" % (e,))
            return None

        self.log.debug("Query: %s" % (str(query),))
        self.log.debug("Type: %s" % (r.type,))

        # if disambiguation, save old result
        # for fallback but try to get the 
        # real abstract
        if r.type == 'disambiguation':
            if r.related:
                detailed_url = r.related[0].url + "?o=x"
                self.log.debug("DDG: disambiguating %s" % (detailed_url,))
                request = requests.get(detailed_url)
                response = request.content
                if response:
                    xml = ElementTree.fromstring(response)
                    r = ddg.Results(xml)

        if (r.answer is not None and r.answer.text and
                "HASH" not in r.answer.text):
            return(query + self.is_verb + r.answer.text + '.')
        elif len(r.abstract.text) > 0:
            sents = split_sentences(r.abstract.text)
            #return sents[0]  # what it is
            #return sents     # what it should be
            return ". ".join(sents)   # what works for now
        elif len(r.related) > 0 and len(r.related[0].text) > 0:
            related = split_sentences(r.related[0].text)[0]
            return(self.format_related(related, query))
        else:
            return None

    def fix_input(self, query):
        for noun in self.translated_question_words:
            for verb in self.translated_question_verbs:
                for article in [i + ' ' for i in self.translated_articles] + ['']:
                    test = noun + verb + ' ' + article
                    if query[:len(test)] == test:
                        return query[len(test):]
        return query

    def CQS_match_query_phrase(self, query):
        answer = None
        for noun in self.translated_question_words:
            for verb in self.translated_question_verbs:
                for article in [i + ' ' for i in self.translated_articles] + ['']:
                    test = noun + verb + ' ' + article
                    if query[:len(test)] == test:
                        answer = self.respond(query[len(test):])
                        break
        if answer:
            return (query, CQSMatchLevel.CATEGORY, answer)
        else:
            self.log.debug("DDG has no answer")
            return None

    def stop(self):
        pass

    @intent_handler(IntentBuilder("AskDucky").require("DuckDuckGo"))
    def handle_ask_ducky(self, message):
        """entry point when ddg is called out by name
           in the utterance"""
        utt = message.data['utterance']

        if utt is None:
            return

        for voc in self.sorted_vocab:
            utt = utt.replace(voc,"")

        utt = utt.strip()
        utt = self.fix_input(utt)
        utt = utt.replace("an ","")   # ugh!
        utt = utt.replace("a ","")   # ugh!
        utt = utt.replace("the ","")   # ugh!

        if utt is not None:
            response = self.respond(utt)
            if response is not None:
                self.speak_dialog("ddg.specific.response")
                self.speak(response)

def create_skill():
    return DuckduckgoSkill()
