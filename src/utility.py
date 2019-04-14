#!/usr/bin/env python3

"""Contains miscellaneous functions for use in the bot."""

import re


def remove_emoji(txt):
    """Returns <txt> (<str>) without emoji."""
    pattern = ("[\U0001F600-\U0001F64F"
               + "\U0001F300-\U0001F5FF"
               + "\U0001F680-\U0001F6FF"
               + "\U0001F1E0-\U0001F1FF]+")
    return re.sub(pattern, "", txt)


def shorten(string, maxLen, last):
    """Returns <string> with custom truncation.

    Keyword arguments:
        string -- <str>; the text to shorten
        maxLen -- <int>; the maximum number of characters <string> can
                  be
        last -- <str>; truncates <string> to <last> found closest before
                <maxLen> if <maxLen> is less than the length of <string>

    Example:
        # Shortens <sentence> to <"."> found just before 45 characters
        # giving <"Hi everyone! My name is Indiana Jones.">
        sentence = "Hi everyone! My name is Indiana Jones. How are you?"
        shortened = shorten(sentence, 45, ".")
    """
    if len(string) <= maxLen:
        return string
    string = string[:maxLen]
    string = string[::-1]
    found = re.search(re.escape(last), string)
    if found:
        string = string[found.start():]
    string = string[::-1]
    return string


def shorten_lines(string, lineLen, maxLines):
    """Truncates <string> to a certain number of lines.

    Keyword arguments:
        string -- <str>; the <str> to shorten
        lineLen -- <int>; the number of characters that constitute one
                   line
        maxLines -- <int>; the number of lines <string> can be at most
    """
    lines = string.split("\n")
    lineCount = 0
    newLines = ""
    for line in lines:
        length = int(len(line) / lineLen) if len(line) > lineLen else 1
        if len(line) > length * lineLen:
            length += 1
        lineCount += length
        if lineCount > maxLines:
            break
        newLines += "{}\n".format(line)
    return newLines


def identical_item(list1, list2):
    """Returns the first common element.

    Return values:
        If a common element in list1 (<list>) and list2 (<list>) was
        found, that element will be returned. Otherwise, <None> will be
        returned.
    """
    for item in list1:
        for part in list2:
            if item == part:
                return item
    return None
