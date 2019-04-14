#!/usr/bin/env python3

import random
import re
import string


def strengthen(pwd, spChars=True):
    """Returns a strengthened password (<str>).

    Keyword arguments:
        pwd -- <str>; the password to strengthen
        spChars -- <bool>; specifies if special characters can be used
                   in the password
    """
    spCharsSet = ("{", "}", "(", ")", "[", "]", "#", ":", ";", "^", ",", ".",
                  "?", "!", "|", "&", "_", "`", "~", "@", "$", "%", "/", "\\",
                  "+", "-", "*", "=", "'", "\"")
    rand = random.SystemRandom()
    if spChars and not re.search(r"[^a-zA-Z0-9]", pwd):
        pwd += spCharsSet[rand.randrange(30)]
    if not re.search(r"[0-9]", pwd):
        pwd = re.sub("o|O", "0", pwd)
        pwd = re.sub("i|I", "1", pwd)
        pwd = re.sub("z|Z", "2", pwd)
        pwd = re.sub("e|E", "3", pwd)
        pwd = re.sub("A", "4", pwd)
        pwd = re.sub("s|S", "5", pwd)
        pwd = re.sub("G", "6", pwd)
        pwd = re.sub("B", "8", pwd)
        if not re.search(r"[0-9]", pwd):
            pwd += str(rand.randrange(10))
    ltr = tuple(string.ascii_lowercase)
    if len(re.findall(r"[a-zA-Z]", pwd)) < 2:
        pwd += ltr[rand.randrange(26)] + ltr[rand.randrange(26)].upper()
    if not re.findall(r"[a-z]", pwd):
        span = re.search(r"[A-Z]", pwd)
        char = pwd[span.start():span.end()]
        pwd = re.sub(char, char.lower(), pwd, 1)
    if not re.findall(r"[A-Z]", pwd):
        span = re.search(r"[a-z]", pwd)
        char = pwd[span.start():span.end()]
        pwd = re.sub(char, char.upper(), pwd, 1)
    if len(pwd) < 12:
        chars = ltr + ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10")
        if spChars:
            chars += spCharsSet
        for char in range(12 - len(pwd)):
            pwd += chars[rand.randrange(len(chars))]
    return pwd
