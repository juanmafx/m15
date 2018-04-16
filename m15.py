# -*- coding: utf-8 -*-
"""
Created on Sun Apr 15 22:57:47 2018

@author: J
"""
import csv
with open('Bitcoin15.csv', 'wb') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter=' ',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
    spamwriter.writerow(['Spam'] * 5 + ['Baked Beans'])
    spamwriter.writerow(['Spam', 'Lovely Spam', 'Wonderful Spam'])

print ("Corio")

