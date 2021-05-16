
txt = 'Risszeichnungen (Band 8)'
txt_list = [int(s) for s in txt.split() if s.isdigit()]
print(txt_list)

a_string = "0abc 1 def23"
numbers = [int(word) for word in a_string.split() if word.isdigit()]
print(numbers)

import re
# initializing string
test_string = "There are 2 apples for 4persons"
# printing original string
print("The original string : " + test_string)
# using re.findall()
# getting numbers from string
temp = re.findall(r'\d+', test_string)
res = list(map(int, re.findall(r'\d+', test_string)))
# print result
print("The numbers list is : " + str(res))