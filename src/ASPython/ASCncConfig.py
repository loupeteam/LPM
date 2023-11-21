'''
 * File: ASCncConfig.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
'''
AS Tools - Cnc Config

This package contains functions necessary to perform actions on 
AS Cnc Configuration files outside of Automation Studio. 

Requires lxml
'''

import os.path
# import xml.etree.ElementTree as ET
import lxml.etree as ET

__version__ = '0.0.0.1'

def listOfProcs(tree, include_comments=False):
    procs = []
    for node in tree.xpath('//BuiltInProcs'):
        for child in node:
            if child.tag is not ET.Comment:
                if include_comments and child.getprevious() is not None and child.getprevious().tag is ET.Comment:
                    print("<!-- " + child.getprevious().text + "-->")
                    procs.append(child.getprevious())
                print(child.tag)
                procs.append(child)
    return procs

def main():
    tree = ET.parse('test/gmcipubr.cnc')

    # print(ET.tostring(tree, pretty_print=True))
    listOfProcs(tree, include_comments=True)


if __name__ == "__main__":
    main()

