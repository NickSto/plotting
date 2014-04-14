#!/usr/bin/env python
#TODO: Attributes. Probably best to allow them to be set on any unique "thing".
#      e.g. (account), (account, section), (account, section, key), or
#      (account, section, key, value).
#TODO: Note whether a line conformed to the new standards or not (attribute).
#TODO: Finish strict mode.
#TODO: Deal with comments at the ends of lines  # like this
#      but somehow allow in things like "account #:" or "PIN#"
#TODO: Recognize section names like "[for credit card]" and tag appropriately
#TODO: Deal with "[deleted] notes"
#      For sites or accounts that are deleted, just add a 'deleted' key = True
#TOOD: Ideally, this should allow preservation of the original formatting of the
#      file, including all unrecognized lines. Then I could use this to actually
#      edit the file and overwrite it without losing any information.
from __future__ import division
import re
import collections

TOP_LEVEL_REGEX     = r'^>>([^>]+)\s*$'
SUPER_SECTION_REGEX = r'^>([^>]+)\s*$'
SITE_REGEX          = r'^(\S(?:.*\S)):\s*$'
SITE_URL_REGEX      = r'^((?:.+://)?[^.]+\.[^.]+.+):\s*$'
SITE_ALIAS_REGEX    = r' \(([^)]+)\):\s*$'
ACCOUNT_NUM_REGEX   = r'^\s+{account ?(\d+)}\s*$' # new account num format
SECTION_REGEX1      = r'^\s+\[([\w#. -]+)\]\s*$'
SECTION_REGEX2      = r'^ {3,5}(\S(?:.*\S)):\s*$'
KEYVAL_REGEX        = r'^\s+(\S(?:.*\S)?):\s*(\S.*)$'
KEYVAL_NEW_REGEX    = r'^\t(\S(?:.*\S)?):\t+(\S(?:.*\S)?)\s*$'
FLAG_REGEX          = r'^\s+\*\*([^*]+)\*\*\s*$'
# Special cases
URL_LINE_REGEX      = r'^((?:.+://)?[^.]+\.[^.]+.+)\s*$'
QLN_LINE_REGEX      = r'^\s+(QLN)(?:\s+\S.*$|\s*$)'
CC_LINE_REGEX       = r'\s*\*.*credit card.*\*\s*'


"""
Strict mode - current rules:
Ignore old-style section lines.
Don't do fuzzy credit card line matching.
Ignore QLN lines.
"""


class AccountsReader(list):
  def __init__(self, filepath, strict=False):
    if strict:
      raise NotImplementedError
    super(AccountsReader, self).__init__()
    self.errors = []
    self._parse_accounts(filepath, strict)

  def _parse_accounts(self, filepath, strict):
    """The parsing engine itself."""
    line_num = 0
    last_line = None
    top_level = None
    super_section = None
    entry = None
    with open(filepath, 'rU') as filehandle:
      for line_raw in filehandle:
        line_num+=1
        line = line_raw.rstrip('\r\n')
        # Skip blank or commented lines
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith('#'):
          continue

        # At a top-level section heading?
        # (In addition to matching the regex, the previous line must contain
        # at least 20 "="s in a row.)
        if last_line is not None and '=' * 20 in last_line:
          top_level_match = re.search(TOP_LEVEL_REGEX, line)
          if top_level_match:
            top_level = top_level_match.group(1).lower()
            last_line = line
            continue

        # At a 2nd-level section heading?
        # (Previous line must contain at least 20 "-"s in a row.)
        if last_line is not None and '-' * 20 in last_line:
          super_section_match = re.search(SUPER_SECTION_REGEX, line)
          if super_section_match:
            super_section = super_section_match.group(1).lower()
            last_line = line
            continue

        # Parse 'online' top-level section (the one with the account info)
        if top_level == 'online' and super_section == 'accounts':

          # Are we at the start of an entry?
          site_match = re.search(SITE_REGEX, line)
          if site_match:
            # Store previous entry and initialize a new one
            if entry is not None:
              self.append(entry)
            entry = AccountsEntry()
            # Determine and set the site name, alias, and url
            entry.site = site_match.group(1)
            site_url_match = re.search(SITE_URL_REGEX, line)
            if site_url_match:
              entry.site = site_url_match.group(1)
              entry.site_alias = None
              site_alias_match = re.search(SITE_ALIAS_REGEX, line)
              if site_alias_match:
                entry.site_alias = site_alias_match.group(1)
                site_old = entry.site
                entry.site = site_old.replace(' ('+entry.site_alias+')', '')
                if entry.site == site_old:
                  message = ('Failed to remove alias "'+entry.site_alias+
                    '" from site name "'+entry.site+'"')
                  self.errors.append(
                    {'message':message, 'line':line_num, 'data':line}
                  )
            account = 0
            section = 'default'
            last_line = line
            continue

          # If we don't know what entry we're in, skip the rest and get back to
          # looking for an entry header.
          if entry is None:
            last_line = line
            continue

          # What kind of data line are we on?
          account_num_match = re.search(ACCOUNT_NUM_REGEX, line)
          section_match1 = re.search(SECTION_REGEX1, line)
          section_match2 = re.search(SECTION_REGEX2, line)
          keyval_match = re.search(KEYVAL_REGEX, line)
          flag_match = re.search(FLAG_REGEX, line)
          if account_num_match:
            account = int(account_num_match.group(1))
            section = 'default'
          elif section_match1 or section_match2:
            # start of section
            if section_match1:
              section = section_match1.group(1)
            else:
              if strict:
                message = 'Strict mode error: old section line format'
                self.errors.append(
                  {'message':message, 'line':line_num, 'data':line}
                )
              else:
                section = section_match2.group(1)
          elif keyval_match:
            # a key/value data line
            keyval_new_match = re.search(KEYVAL_NEW_REGEX, line)
            if keyval_new_match:
              field = keyval_new_match.group(1)
              value = keyval_new_match.group(2)
            else:
              field = keyval_match.group(1)
              value = keyval_match.group(2)
            if ';' in value:
              # multiple values?
              value = [elem.strip() for elem in value.split(';')]
            self._safe_add(entry, (account, section, field), value)
          elif flag_match:
            field = flag_match.group(1)
            self._safe_add(entry, (account, section, field), True)
          elif '=' * 20 in line or '-' * 20 in line:
            # heading divider
            pass
          else:
            # Test for special case lines
            qln_match = re.search(QLN_LINE_REGEX, line)
            cc_line_match = re.search(CC_LINE_REGEX, line)
            url_line_match = re.search(URL_LINE_REGEX, line)
            site_last_match = re.search(SITE_REGEX, last_line)
            if url_line_match and site_last_match:
              # URL on line after entry heading
              entry.site_alias = site_last_match.group(1)
              entry.site = url_line_match.group(1)
            elif qln_match:
              # "QLN"-type shorthand
              if strict:
                message = 'Strict mode error: QLN line'
                self.errors.append(
                  {'message':message, 'line':line_num, 'data':line}
                )
              else:
                self._add_qln(entry, account, section)
            elif cc_line_match:
              # "stored credit card" note
              if strict:
                message = 'Strict mode error: nonconforming credit card line'
                self.errors.append(
                  {'message':message, 'line':line_num, 'data':line}
                )
              else:
                entry[(account, section, 'used credit card')] = True
            elif re.search(r'^\S', line):
              # If it's not indented, take the safe route and assume it could be
              # an unrecognized entry header. That means we no longer know which
              # entry we're in.
              entry = None
              message = 'Line is like an entry header, but malformed'
              self.errors.append(
                {'message':message, 'line':line_num, 'data':line}
              )
            else:
              # Unrecognized.
              message = 'Unrecognized line'
              self.errors.append(
                {'message':message, 'line':line_num, 'data':line}
              )

        last_line = line

    if top_level is None:
      message = 'Found no top-level section headings'
      self.errors.append(
        {'message':message, 'line':None, 'data':None}
      )


  def _safe_add(self, entry, key, value):
    """Add key/value only if it doesn't already exist in the entry.
    If it does, don't overwrite it and add an error instead."""
    if key in entry:
      message = 'Duplicate key, section, or account'
      self.errors.append(
        {'message':message, 'line':line_num, 'data':line}
      )
      return False
    else:
      entry[key] = value
      return True


  def _add_qln(self, entry, account, section):
    entry[(account, section, 'username')] = 'qwerty0'
    entry[(account, section, 'password')] = 'least secure'
    entry[(account, section, 'email')] = 'nmapsy'


#TODO: Keep the actual keys (or hell, all the data) in self._accounts, by
#      making each account an OrderedDict mapping sections to either lists of
#      fields or OrderedDicts mapping fields to values (to store all the data).
#      This is what will allow looking up the data in an account or section
#      without reading through all the keys.
class AccountsEntry(collections.OrderedDict):
  """Keys must be either the field name string or a tuple of the account number,
  the section name, and the field name."""
  def __init__(self):
    super(AccountsEntry, self).__init__()
    self.site = None
    self.site_alias = None
    self.site_url = None
    self.default_account = 0
    self.default_section = 'default'
    # Keep track of the accounts and sections that exist in this entry
    # It's a dict of accounts mapped to lists of sections. It looks like:
    # {0:['default', 'old'], 1:['default']}
    self._accounts = collections.OrderedDict()

  def __getitem__(self, key):
    full_key = self.get_full_key(key)
    return collections.OrderedDict.__getitem__(self, full_key)

  def __setitem__(self, key, value):
    (account, section, field) = self.get_full_key(key)
    sections = self._accounts.get(account, [])
    if section not in sections:
      sections.append(section)
    self._accounts[account] = sections
    collections.OrderedDict.__setitem__(self, (account, section, field), value)

  def __contains__(self, key):
    full_key = self.get_full_key(key)
    return collections.OrderedDict.__contains__(self, full_key)

  def update(self):
    raise NotImplementedError

  def get_full_key(self, key):
    """Return a proper, full key for indexing the dict.
    If the input is a string, assume the default account and section.
    If it's a proper 3-tuple, return it unaltered.
    If it's neither, throw an assertion error."""
    #TODO: allow other tuple-like types?
    is_str = isinstance(key, basestring)
    is_proper_tuple = (
      isinstance(key, tuple) and len(key) == 3
      and isinstance(key[0], int)
      and isinstance(key[1], basestring)
      and isinstance(key[2], basestring)
    )
    assert is_str or is_proper_tuple, (
      '"key" must either be a str or tuple of (account, section, fieldname).'
    )
    if is_str:
      full_key = (self.default_account, self.default_section, key)
    else:
      full_key = key
    return full_key

  def accounts(self):
    """Return a tuple of the account numbers in the entry."""
    return tuple(self._accounts.keys())

  def sections(self, account):
    """Return a tuple of the sections in the account.
    Returns () if the account doesn't exist."""
    return tuple(self._accounts.get(account, ()))

  def keys(self, account=None, section=None):
    if account is None and section is None:
      return collections.OrderedDict.keys(self)
    keys = []
    for key in collections.OrderedDict.keys(self):
      if account == key[0] and (section == key[1] or section is None):
        keys.append(key)
    return keys

  def items(self, account=None, section=None):
    if account is None and section is None:
      return collections.OrderedDict.items(self)
    items = []
    # use .keys() implementation to handle which items to get
    for key in self.keys(account=account, section=section):
      items.append((key, self[key]))
    return items