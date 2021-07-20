
import os
import random
import logging

CODE_CACHE = dict()
logger = logging.getLogger(__name__)
LENGTH_BEFORE = 150
LENGTH_AFTER = 300
MAX_FILES_PER_DIR = 300
MAX_DEPTH = 4

def get_file_content(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()
    

def load_source_code_files(code_base_dirs):
    if type(code_base_dirs) != list:
        return
    for base_dir in code_base_dirs:
        for root, dirs, files in os.walk(base_dir):
            if '.git' in root or 'node_modules' in root:
                continue
            if root.count('/') + root.count('\\') > MAX_DEPTH:
                continue
            for i, f in enumerate(files):
                if i > MAX_FILES_PER_DIR:
                    break
                if f.endswith('.py'):
                    path = os.path.join(root, f)
                    try:
                        CODE_CACHE[path] = get_file_content(path)
                    except:
                        pass


def try_init(code_base_dirs):
    if len(CODE_CACHE) == 0:
        load_source_code_files(code_base_dirs)

def search_code(keyword):
    #print('keyword = {}'.format(keyword))
    result = []
    for path, code in CODE_CACHE.items():
        index = code.find(keyword)
        if index == -1:
            continue
        L = index - LENGTH_BEFORE
        R = index + LENGTH_AFTER
        if L < 0:
            L = 0
        if R > len(code):
            R = len(code)
        snippet = code[L:R]
        result.append(snippet)

    #print(result)
    
    if len(result) > 0:
        return result[random.randrange(len(result))]
    else:
        return None
