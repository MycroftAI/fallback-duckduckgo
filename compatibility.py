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

from mycroft.skills.core import FallbackSkill
from mycroft.util import LOG

if sys.version_info[0] >= 3:  # noqa
    import ddg3 as ddg
else:
    import duckduckgo as ddg


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


class DuckduckgoSkill(FallbackSkill):
    # Only ones that make sense in
    # <question_word> <question_verb> <noun>
    question_words = [
        'who', 'whom', 'what', 'when'
    ]
    # Note the spaces
    question_verbs = [
        ' is', '\'s', 's', ' are', '\'re',
        're', ' did', ' was', ' were'
    ]
    articles = ['a', 'an', 'the', 'any']
    start_words = [
        'is', 'and', 'a', 'of', 'if', 'the',
        'because', 'since', 'for', 'by', 'from',
        'when', 'between', 'who', 'was', 'in'
    ]
    is_verb = ' is '
    in_word = 'in '

    def __init__(self):
        super(DuckduckgoSkill, self).__init__()

    def initialize(self):
        self.register_fallback(self.respond_to_question, 10)

    @classmethod
    def format_related(cls, abstract, query):
        LOG.debug('Original abstract: ' + abstract)
        ans = abstract

        if ans[-2:] == '..':
            while ans[-1] == '.':
                ans = ans[:-1]

            phrases = ans.split(', ')
            first = ', '.join(phrases[:-1])
            last = phrases[-1]
            if last.split()[0] in cls.start_words:
                ans = first
            last_word = ans.split(' ')[-1]
            while last_word in cls.start_words or last_word[-3:] == 'ing':
                ans = ans.replace(' ' + last_word, '')
                last_word = ans.split(' ')[-1]

        category = None
        match = re.search('\(([a-z ]+)\)', ans)
        if match:
            start, end = match.span(1)
            if start <= len(query) * 2:
                category = match.group(1)
                ans = ans.replace('(' + category + ')', '()')

        words = ans.split()
        for article in cls.articles:
            article = article.title()
            if article in words:
                index = words.index(article)
                if index <= 2 * len(query.split()):
                    name, desc = words[:index], words[index:]
                    desc[0] = desc[0].lower()
                    ans = ' '.join(name) + cls.is_verb + ' '.join(desc)
                    break

        if category:
            ans = ans.replace('()', cls.in_word + category)

        if ans[-1] not in '.?!':
            ans += '.'
        return ans

    def respond(self, query):
        if len(query) == 0:
            return 0.0

        r = ddg.query(query)

        LOG.debug('Query: ' + str(query))
        LOG.debug('Type: ' + r.type)

        if r.answer is not None and r.answer.text and "HASH" not in r.answer.text:
            self.speak(query + self.is_verb + r.answer.text + '.')
        elif len(r.abstract.text) > 0:
            sents = split_sentences(r.abstract.text)
            self.speak(sents[0])
        elif len(r.related) > 0 and len(r.related[0].text) > 0:
            related = split_sentences(r.related[0].text)[0]
            self.speak(self.format_related(related, query))
        else:
            return False

        return True

    def respond_to_question(self, message):
        query = message.data['utterance']
        for noun in self.question_words:
            for verb in self.question_verbs:
                for article in [i + ' ' for i in self.articles] + ['']:
                    test = noun + verb + ' ' + article
                    if query[:len(test)] == test:
                        return self.respond(query[len(test):])
        return False

    def stop(self):
        pass


def create_skill():
    return DuckduckgoSkill()
