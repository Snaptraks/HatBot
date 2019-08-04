def escape(string):
    return string.translate(str.maketrans({'_': r'\_',
                                           '*': r'\*',
                                           '~': r'~',
                                           '`': r'\`',
                                           '|': r'\|',
                                           '\\': r'\\',
                                           }))
