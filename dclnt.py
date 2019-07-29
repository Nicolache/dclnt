import sys
import ast
import os
import collections
import vcstools
import argparse
import json
import csv

from nltk import pos_tag


Path = ''
repos_local_path = './repos/'
repos_to_clone_urls = [
    ['https://github.com/VladimirFilonov/wsdl2soaplib.git', 'git'],
    ['https://github.com/VladimirFilonov/discogs_client.git', 'git'],
    ['https://github.com/Nicolache/goipsend.git', 'git'],
]


def delete_repos_directories():
    for directory in os.listdir(repos_local_path):
        os.system('rm -rf ' + repos_local_path + '/' + directory)


def repo_clone(https_url, vcs_type):
    reponame = https_url.rsplit('/', 1)[1]
    client = vcstools.VcsClient(vcs_type, repos_local_path + reponame)
    client.checkout(https_url)


def clone_all():
    for url_and_vcstype in repos_to_clone_urls:
        repo_clone(url_and_vcstype[0], url_and_vcstype[1])


def flat(_list):
    """ [(1,2), (3,4)] -> [1, 2, 3, 4]"""
    flat_list = []
    for item in _list:
        flat_list = flat_list + list(item)
    return flat_list


def is_verb(word):
    if not word:
        return False
    pos_info = pos_tag([word])
    return pos_info[0][1] == 'VB'


def get_filenames():
    filenames = []
    path = Path
    for dirname, dirs, files in os.walk(path, topdown=True):
        for file in files:
            if file.endswith('.py'):
                filenames.append(os.path.join(dirname, file))
                if len(filenames) == 100:
                    break
    return filenames


def get_trees(_path, with_filenames=False, with_file_content=False):
    trees = []
    filenames = get_filenames()
    print('total %s files' % len(filenames))
    for filename in filenames:
        with open(filename, 'r', encoding='utf-8') as attempt_handler:
            main_file_content = attempt_handler.read()
        try:
            tree = ast.parse(main_file_content)
        except SyntaxError as e:
            print(e)
            tree = None
        if with_filenames:
            if with_file_content:
                trees.append((filename, main_file_content, tree))
            else:
                trees.append((filename, tree))
        else:
            trees.append(tree)
    print('trees generated')
    return trees


def word_belongs_to_parts_of_speech(word, abbreviations):
    if not word:
        return False
    pos_info = pos_tag([word])
    return pos_info[0][1] in abbreviations


# pos - part of speech
def get_pos_from_function_name(function_name, abbreviations):
    verbs = []
    for word in function_name.split('_'):
        if word_belongs_to_parts_of_speech(word, abbreviations):
            verbs.append(word)
    return verbs


def get_top_pos_in_path(path, abbreviations, top_size=10):
    global Path
    Path = path
    trees = get_trees(None)
    fncs = []
    for t in trees:
        for node in ast.walk(t):
            if isinstance(node, ast.FunctionDef):
                fnc_name = node.name.lower()
                if not (fnc_name.startswith('__') and fnc_name.endswith('__')):
                    fncs.append(fnc_name)
    print('functions extracted')
    v = []
    for function_name in fncs:
        # pos - part of speech
        # abbreviations - pos abbreviations
        v.append(get_pos_from_function_name(function_name, abbreviations))
    parts_of_speech = flat(v)
    return collections.Counter(parts_of_speech).most_common(top_size)


parser = argparse.ArgumentParser()
parser.add_argument(
    '--clear',
    '--clear-local-repos-directory',
    action='store_true',
    help='It removes all the directories \
        inside repos_local_path\
        on start.',
)
parser.add_argument(
    '-c',
    '--clone',
    action='store_true',
    help='It clones all from repos_to_clone_urls.',
)
parser.add_argument(
    '-n',
    '--do-not-count',
    action='store_true',
    help='Do not built statistics.',
)
parser.add_argument(
    '-V',
    '--verbs',
    action='store_true',
    help='Build statistics of the most frequent verbs.',
)
parser.add_argument(
    '-N',
    '--nouns',
    action='store_true',
    help='Build statistics of the most frequent nouns.',
)
parser.add_argument(
    '-j',
    '--json',
    action='store_true',
    help='Store in json format.',
)
parser.add_argument(
    '-cs',
    '--csv',
    action='store_true',
    help='Store in csv format.',
)
parser.add_argument(
    '-o',
    '--output',
    action='store',
    type=str,
    help="Redirect output to a file.",
)
args = parser.parse_args()

if args.clear:
    delete_repos_directories()

if args.clone:
    clone_all()

if not args.do_not_count and (args.nouns or args.verbs):
    wds = []
    projects = [
        'django',
        'discogs_client.git',
        'goipsend.git',
        'wsdl2soaplib.git',
        'flask',
        'pyramid',
        'reddit',
        'requests',
        'sqlalchemy',
    ]
    for project in projects:
        path = os.path.join('.', project)
        if args.nouns:
            wds += get_top_pos_in_path(path, ['NN', 'NNS', 'NNP', 'NNPS'])
        if args.verbs:
            wds += get_top_pos_in_path(path, ['VB'])
    
    top_size = 200

    if not (args.json or args.csv):
        print('total %s words, %s unique' % (len(wds), len(set(wds))))
        for word, occurence in collections.Counter(wds).most_common(top_size):
            print(word, occurence)

    if args.json:
        dict_for_json = {}
        for word, occurence in collections.Counter(wds).most_common(top_size):
            dict_for_json.update({word[0]: (word[1], occurence)})
        with open(args.output, "w") as write_file:
            json.dump(dict_for_json, write_file)

    if args.csv:
        list_for_csv = []
        for word, occurence in collections.Counter(wds).most_common(top_size):
            list_for_csv.append([word[0], word[1], occurence])
        with open(args.output, "w") as write_file:
            writer = csv.writer(write_file, delimiter=',')
            for line in list_for_csv:
                writer.writerow(line)
