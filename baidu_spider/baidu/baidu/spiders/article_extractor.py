import re
from time import time
from newspaper import Article
from fuzzywuzzy import process
from fuzzysearch import find_near_matches
from difflib import SequenceMatcher
import lxml
from lxml.html.clean import Cleaner
from io import StringIO
# from extraction.lib.date_extractor import extractArticlePublishedDate
from datetime import datetime

from date_extractor import extractArticlePublishedDate

blank_pat = re.compile(r'\s+')
single_blank_pat = re.compile(r'\s')
all_digit_pat = re.compile(r'^\d*$')
title_sep_pat = re.compile(r'[-_|－]')   #—
site_name_end_pat = re.compile(r'(网|在线|门户|频道|栏目|站点?|新闻|政府|办公室)$')
escape_pat = re.compile(r'&(nbsp|lt|gt);')
single_punc_pat = re.compile(r'[^ 0-9A-Za-z\u4E00-\u9FFF]')
article_date_pat = re.compile(r'(?:^|[^-+\d])((?:19|20)?\d{2})([\./\-_年]?)(1[0-2]|0?[1-9])([\./\-_月]?)([1-2][0-9]|3[0-1]|0?[1-9])' +
                              r'(?:[^-+:\d](?:\s*((?:1|0?)[0-9]|2[0-3])[:点时]((?:[1-5]|0?)[0-9])(?:[:分]((?:[1-5]|0?)[0-9]))?(?:[^-+:\d]|$))?|$)')
blank_date_pat = re.compile(r'(?<!\d)\s|\s(?!\d)')
time_prefix_pat = re.compile(r'时间|日期|时期|发表|发布|提交|上传|于')
html_body_pat = re.compile(r'<\s*/\s*(html|body)\s*>', re.IGNORECASE)


cleaner = Cleaner()
cleaner.javascript = True # This is True because we want to activate the javascript filter
cleaner.style = True      # This is True because we want to activate the styles & stylesheet filter


def remove_blanks(text):
  text = blank_pat.sub(' ', text)
  return blank_date_pat.sub('', text)


def strip_site_names_from_title(title):
  title = title_sep_pat.split(title, 1)[0].strip()
  parts = title.split()
  while len(parts) > 1:
    if site_name_end_pat.search(parts[-1]):
      parts.pop()
    else:
      break

  return ' '.join(parts)


def find_ignoring_spaces(text, sub):
  parts = sub.split()
  start = 0
  end = 0
  for part in parts:
    if part:
      start = text.find(part, end)
      # All searches after the first can't jump over non-blank chars
      if start >= 0 and (end == 0 or text[end:start].strip() == ''):
        end = start + len(part)
      else:
        start = -1
        break

  return (start, end)


def get_content_index(title, content):
  # Get prefix: first 20 chars, expanding to the end of the line
  start = 0

  if content:
    idx = content.find('\n', 20)
    if idx >= 0:
      prefix = content[:idx + 20]
    else:
      prefix = content

    lines = prefix.split('\n')
    tt = single_punc_pat.sub('-', single_blank_pat.sub(' ', title))
    if tt:
      for i, ln in enumerate(lines):
        ln = single_punc_pat.sub('-', single_blank_pat.sub(' ', ln))
        start_idx, end_idx = find_ignoring_spaces(ln, tt)
        if start_idx >= 0:
          if start_idx == 0 or end_idx == len(ln) or (blank_pat.search(ln[start_idx - 1]) and blank_pat.search(ln[end_idx])):
            # Decide whether the entire line isn't part of the content
            # TODO: Add special conditions for phrases like "publish time", "author", "views", etc
            if len(ln) > len(tt) + 40:
              start += end_idx
            else:
              start += len(lines[i]) + 1

            content = content[start:]
            start += get_content_index(title, content)
            return start

        start += len(lines[i]) + 1

  return 0


def select_date_from_candidates(dates, order=-1, text=''):
  if order == -1:
    series = range(len(dates) - 1, -1, -1)
  else:
    series = range(len(dates))

  result = None
  res_date = None
  has_prefix = None
  has_time = None
  distance = None
  for i in series:
    candidate = dates[i]
    groups = candidate.groups()
    if len(groups) == 8:
      if groups[1] == '年' or groups[3] == '月':
        if not (groups[1] == '年' and groups[3] == '月'):
          continue
      else:
        if groups[1] != groups[3]:
          continue
        elif not groups[1]:
          if len(groups[0]) + len(groups[2]) + len(groups[4]) != 8:
            continue

      parts = [int(groups[0]), int(groups[2]), int(groups[4])]

      if parts[0] < 100:
        # 2-digit year, convert to 4-digit year
        parts[0] += 2000
        if parts[0] > datetime.now().year:
          parts[0] -= 100

      if groups[5] and groups[6]:
        parts += [int(groups[5]), int(groups[6]), int(groups[7] or 0)]
        has_time = True
      else:
        has_time = False

      try:
        date = datetime(*parts)
      except ValueError:
        continue
      if date.year >= 1980 and date.year <= datetime.now().year:
        res_date = date
        prefix = text[:candidate.start()].strip()[-5:]
        has_prefix = bool(time_prefix_pat.search(prefix))
        if order == -1:
          distance = len(text) - candidate.end()
        else:
          distance = candidate.start()

        if has_prefix or has_time:
          result = (res_date, has_prefix or has_time, distance)
          break
        elif result is None:
          result = (res_date, has_prefix or has_time, distance)
      else:
        continue

  return result or (res_date, has_prefix or has_time, distance)


def extract_article(url, html):
  article = Article(url, language='zh')

  # Special handling: make sure </html> is at the end of the document
  html = html_body_pat.sub(' ', html) + '</body></html>'
  article.download(input_html = html)

  article.parse()
  top_node = article.top_node
  title = article.title
  meta_title = None
  h1_title = None
  if len(article.titles) > 1:
    meta_title = article.titles[0]
    h1_title = article.titles[1]

    if top_node is not None:
      # Select best title according to content
      content = ''.join(top_node.itertext())
      score1 = SequenceMatcher(None, article.titles[0], content).ratio()
      score2 = SequenceMatcher(None, article.titles[1], content).ratio()

      if score1 >= score2:
        title = article.title
      else:
        title = article.titles[1]

  title = strip_site_names_from_title(title).strip()
  if meta_title:
    meta_title = strip_site_names_from_title(meta_title).strip()
  if h1_title:
    h1_title = strip_site_names_from_title(h1_title).strip()

  if title and len(title) > 6 and len(article.top_nodes) > 1:
    # Select best content according to title
    content_map = {}
    for node in article.top_nodes:
      content = escape_pat.sub(' ', ''.join(node.itertext()))
      content = blank_pat.sub('', content[get_content_index(title, content):])
      if content not in content_map:
        content_map[content] = node

    bests = process.extractBests(title, content_map.keys())
    if content_map[bests[0][0]] != article.top_node:
      top_score = 0
      top_len = 0
      for item in bests:
        if content_map[item[0]] == article.top_node:
          top_score = item[1]
          top_len = len(item[0])

      if bests[0][1] > top_score * 2 and (len(bests[0]) >= 50 or len(bests[0]) >= top_len / 2):
        top_node = content_map[bests[0][0]]

  if len(article.top_nodes) > 1:
    # Promote to parent if similar to siblings
    top_text = blank_pat.sub('', ''.join(top_node.itertext()))
    for node in article.top_nodes:
      node_text = None
      if node == top_node.getparent():
        node_text = blank_pat.sub('', ''.join(node.itertext()))
        node_text = node_text.replace(top_text, '')
      elif node.getparent() == top_node.getparent():
        node_text = blank_pat.sub('', ''.join(node.itertext()))

      if node_text:
        s = SequenceMatcher(None, top_text, node_text)
        if s.ratio() >= 0.15:
          top_node = top_node.getparent()
          break

  if top_node is None:
    # Try to identify top_node
    # First search for title in html_text
    tree = cleaner.clean_html(lxml.html.parse(StringIO(article.html)))
    #parser = etree.HTMLParser()
    #tree = etree.parse(StringIO(article.html), parser)
    elem = tree.getroot()
    while True:
      children = list(elem)
      node = None
      for i in range(len(children) - 1, -1, -1):
        child = children[i]
        try:
          if ''.join(child.itertext()).find(title) >= 0:
            node = child
            break
        except:
          pass

      if node is not None:
        elem = node
      else:
        break

    # elem is the smallest element containing the title
    length = len(''.join(elem.itertext()).strip())
    while True:
      node = elem.getparent()
      if node is not None:
        parent_length = len(''.join(node.itertext()).strip())
        if parent_length >= length * 3:
          top_node = node
          break
      else:
        top_node = elem
        break

      elem = node

  content = escape_pat.sub(' ', article.format_top_node(top_node, title))

  # Try to identify date
  index = get_content_index(title, content)
  article_title = title
  article_text = content[index:].strip()
  article_content = article_text

  if not article_text:
    at = content[:index].strip()
    if at:
      article_text = at
    else:
      article_text = title
    article_title = ''

  tree = cleaner.clean_html(lxml.html.parse(StringIO(article.html)))
  html_text = ' '.join(tree.getroot().itertext())
  html_text = remove_blanks(html_text)
  filtered_article_title = remove_blanks(article_title)
  filtered_article_text = remove_blanks(article_text)

  title_start_idx = -1
  title_end_idx = -1
  content_idx = -1
  res_date = None
  if filtered_article_text:
    x = find_near_matches(filtered_article_text, html_text, max_l_dist=2)
    if x:
      content_idx = x[0].start
      if filtered_article_title:
        y = find_near_matches(filtered_article_title, html_text[:content_idx], max_l_dist=2)
        if y:
          title_start_idx = y[-1].start
          title_end_idx = y[-1].end
    else:
      title_lines = article_title.split('\n')
      article_lines = article_text.split('\n')

      end = len(html_text)
      nxt = end
      for i in range(len(article_lines) - 1, -1, -1):
        ln = remove_blanks(article_lines[i])
        if len(ln) >= 10:
          x = find_near_matches(ln, html_text[:end], max_l_dist=2)
          if x:
            end = x[-1].start
            nxt = x[-1].end
          else:
            break

      content_idx = end

      for i in range(len(title_lines) - 1, -1, -1):
        ln = remove_blanks(title_lines[i])
        if len(ln) >= 10:
          x = find_near_matches(ln, html_text[:end], max_l_dist=2)
          if x:
            end = x[-1].start
            nxt = x[-1].end
          else:
            break

      title_start_idx = end
      title_end_idx = nxt

    if title_start_idx >= 0:
      text_between = html_text[title_end_idx:content_idx]
      dates_between = list(article_date_pat.finditer(text_between))
      res_date, res_date_verified, distance = select_date_from_candidates(dates_between, -1, text_between)

    if not (res_date and res_date_verified):
      if title_start_idx >= 0:
        search_end = title_start_idx
      else:
        search_end = content_idx

      text_before = html_text[:search_end]
      dates_before = list(article_date_pat.finditer(text_before))
      res_before, res_before_verified, dist_before = select_date_from_candidates(dates_before, -1, text_before)

      text_after = html_text[content_idx:]
      dates_after = list(article_date_pat.finditer(text_after))
      res_after, res_after_verified, dist_after = select_date_from_candidates(dates_after, 1, text_after)

      if res_before:
        if res_after:
          if res_before_verified and not res_after_verified:
            res_date = res_before
            res_date_verified = True
          elif res_after_verified and not res_before_verified:
            res_date = res_after
            res_date_verified = True
          elif dist_before <= dist_after:
            if res_before_verified or not res_date:
              res_date = res_before
              res_date_verified = res_before_verified
          else:
            if res_after_verified or not res_date:
              res_date = res_after
              res_date_verified = res_after_verified
        else:
          if res_before_verified or not res_date:
            res_date = res_before
            res_date_verified = res_before_verified
      elif res_after:
        if res_after_verified or not res_date:
          res_date = res_after
          res_date_verified = res_after_verified

  extracted_date = extractArticlePublishedDate(url, html=article.html)

  # Date from meta tags
  if article.publish_date:
    if not (res_date and res_date.date() == article.publish_date.date()):
      res_date = article.publish_date
  # Date from URL
  elif extracted_date and not (res_date and res_date_verified):
    res_date = extracted_date

  return (title, meta_title, h1_title, article_content, res_date, extracted_date, article.publish_date)

