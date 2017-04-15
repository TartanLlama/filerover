"""Contains a method to check if a file is text or not

Derived from code found here http://code.activestate.com/recipes/173220-test-if-a-file-or-string-is-text-or-binary/"""

import string, sys

text_characters = "".join(map(chr, range(32, 127)) + list("\n\r\t\b"))
_null_trans = string.maketrans("", "")

def istextfile(filename, blocksize = 512):
    """Given a filename, return True if the file is text, False otherwise"""
    return istext(open(filename).read(blocksize))

def istext(s):
    """For internal use only"""
    if "\0" in s:
        return False
    
    if not s:  # Empty files are considered text
        return True

    # Get the non-text characters (maps a character to itself then
    # use the 'remove' option to get rid of the text characters.)
    t = s.translate(_null_trans, text_characters)

    # If more than 30% non-text characters, then
    # this is considered a binary file
    if float(len(t))/len(s) > 0.30:
        return False
    return True
