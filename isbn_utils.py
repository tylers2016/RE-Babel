# 文件名: isbn_utils.py

import re

def sanitize(isbn_str):
    """移除ISBN字符串中的破折号和空格"""
    return isbn_str.replace("-", "").replace(" ", "")

def _is_valid_isbn10(isbn):
    """校验10位ISBN的校验码"""
    if not re.match(r"^\d{9}[\dX]$", isbn):
        return False
    total = 0
    for i in range(9):
        total += int(isbn[i]) * (10 - i)
    last_digit = isbn[9]
    if last_digit == 'X':
        total += 10
    else:
        total += int(last_digit)
    return total % 11 == 0

def _is_valid_isbn13(isbn):
    """校验13位ISBN的校验码"""
    if not re.match(r"^\d{13}$", isbn):
        return False
    total = 0
    for i in range(12):
        digit = int(isbn[i])
        total += digit * (1 if i % 2 == 0 else 3)
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(isbn[12])

def is_valid_isbn(isbn_str):
    """
    主校验函数，净化后判断是10位还是13位，并进行相应校验
    """
    isbn = sanitize(isbn_str)
    if len(isbn) == 10:
        return _is_valid_isbn10(isbn)
    if len(isbn) == 13:
        return _is_valid_isbn13(isbn)
    return False

def convert_10_to_13(isbn10):
    """将10位ISBN转换为13位"""
    stem = "978" + sanitize(isbn10)[:-1]
    total = 0
    for i in range(12):
        digit = int(stem[i])
        total += digit * (1 if i % 2 == 0 else 3)
    check_digit = (10 - (total % 10)) % 10
    return stem + str(check_digit)

def convert_13_to_10(isbn13):
    """将13位ISBN转换为10位，如果不是978开头则返回None"""
    isbn = sanitize(isbn13)
    if not isbn.startswith("978"):
        return None
    stem = isbn[3:-1]
    total = 0
    for i in range(9):
        total += int(stem[i]) * (10 - i)
    check_digit_val = (11 - (total % 11)) % 11
    if check_digit_val == 10:
        check_digit = 'X'
    else:
        check_digit = str(check_digit_val)
    return stem + check_digit