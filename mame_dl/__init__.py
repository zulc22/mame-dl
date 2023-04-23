import mame_dl.defaultsources
import argparse
import sys
import os, os.path
import requests
import urllib.parse
import json
import subprocess
import re
from bs4 import BeautifulSoup

# clean up and exit
def exitpath():
    global LASTDIR
    os.chdir(LASTDIR) # Restore the last directory
    exit()

# load ~/.mame-dl/db.json into DATABASE
def loadDatabase():
    if not os.path.exists("db.json"):
        # Warning for new use
        print("No database! Run 'mame-dl update' to generate it.")
        exitpath()
    with open("db.json") as fp:
        global DATABASE
        DATABASE = json.load(fp)

# load ~/.mame-dl/conf.json into CONFIG    
def loadConfig():
    global CONFIG
    if not os.path.exists("conf.json"):
        # Warning for new use
        print("Configuration required!\n"+
            "Set the MAME install directory with 'mame-dl config mamedir [PATH]'.")
        exitpath()
    with open("conf.json") as fp:
        CONFIG = json.load(fp)
        

# change a value in CONFIG and save to disk
def saveConfig(k,v):
    global CONFIG
    if os.path.exists("conf.json"):
        # ~/.mame-dl/conf.json exists.
        # load it if it hasn't been yet, and make the change
        if 'CONFIG' not in globals():
            with open("conf.json") as fp:
                CONFIG = json.load(fp)
        CONFIG[k] = v
        with open("conf.json","w") as fp:
            json.dump(CONFIG, fp)
    else:
        # ~/.mame-dl/conf.json *doesn't* exist
        # initialize CONFIG with the value we're writing
        CONFIG = {k: v}
        with open("conf.json","w") as fp:
            json.dump(CONFIG, fp)

# $ mame-dl config
def cli_config(args): 
    global LASTDIR, MDL_PATH
    if args.key == "mamedir": # detect the MAME directory
        # change the directory back so that we can calculate relative paths correctly
        os.chdir(LASTDIR)
        directory = os.path.abspath(args.value)
        os.chdir(MDL_PATH)
        if not os.path.exists(directory):
            print("Invalid directory",directory)
            exitpath()
        # go a subfolder up if we are given a roms directory
        if os.path.basename(directory) == "roms":
            directory = os.path.abspath(directory+os.path.sep+"..")
        # add a (back)slash to the end if it's not there (so that we dont need to add it for every folder concat)
        if directory[-1] != os.path.sep: directory += os.path.sep
        # check for a roms directory (where we will be saving the files)
        if not os.path.exists(directory+"roms"):
            print("That path exists, but it isn't a 'roms' directory, nor does it contain one.\n"+
                "Are you sure you specified a path to a MAME installation?")
            exitpath()
        
        print("Set successfully to",directory)
        saveConfig("mamedir", directory)
    else:
        print("Unknown config option",args.key)

# $ mame-dl del
def cli_del(args):
    loadConfig()
    # just delete whatever machine was specified if it exists
    # (machines are stored in mame/roms/MACHINE.zip)
    for m in args.machines:
        zip = CONFIG['mamedir'] + "roms" + os.path.sep + m + ".zip"
        if os.path.exists(zip):
            os.unlink(zip)
        else:
            print(f"- '{m}' doesn't exist in the roms directory, silly!")
            exitpath()

# $ mame-dl add
def cli_add(args):

    loadConfig()
    loadDatabase()
    
    for m in args.machines:
        
        zip = m if m.endswith(".zip") else m+".zip"

        if zip not in DATABASE:
            print(f"- No such machine '{m}' was found.")
            exitpath()

        path = os.path.join(CONFIG['mamedir'], "roms", zip)
        if os.path.exists(path):
            if args.force: os.unlink(path) # -F redownloads if it exists
            else:
                print(f"- '{m}' already exists in the roms directory, silly!")
                continue

        if os.path.exists(path+".tmp"): # remove a temp download if it exists
            os.unlink(path+".tmp")

        os.chdir(CONFIG['mamedir']+"roms")

        # download the .zip with wget (named as a .tmp file)
        subprocess.run([
            "wget",
            "-q","--show-progress","--progress=bar:force:noscroll",
            "-O",zip+".tmp",
            DATABASE[zip]
        ])
        # rename it to the intended filename
        os.rename(zip+".tmp", zip)

# $ mame-get search
def cli_search(args):
    loadDatabase()

    if args.regex:
        for i in DATABASE:
            i = i[:-4] # remove .zip extension
            if re.match(args.query, i):
                print(i)
    else:
        for i in DATABASE:
            i = i[:-4]
            if args.query in i:
                print(i)

def cli_update(args):
    if not os.path.exists("sources.cfg"):
        print("No sources.cfg file, writing defaults\n")
        with open('sources.cfg', 'w') as fp:
            fp.write(defaultsources.DEFAULTSOURCES)

    with open('sources.cfg') as fp:
        # remove all newlines
        SOURCES = [i[:-1] if i.endswith('\n') else i for i in fp.readlines()]
    
    # for progress display
    SOURCESlen = len(SOURCES)
    SOURCESi = 1

    DATABASE = {}
    lastDatabaseSize = 0 # for reporting of new files

    for link in SOURCES:
        print(f"Source {SOURCESi} of {SOURCESlen}: {link}")

        print("Requesting...",end=' '); sys.stdout.flush()
        page = requests.get(link)
        page.raise_for_status() # throw an error if it's not 200

        print("Parsing...",end=' '); sys.stdout.flush()
        pagesoup = BeautifulSoup(page.content, "html.parser")
        # catalogue any links that claim to be .zip files and aren't already saved
        for e in pagesoup.find_all('a'):
            if e.string and e.string.endswith(".zip") and e.string not in DATABASE:
                DATABASE[e.string] = urllib.parse.urljoin(link+"/", e.get('href'))

        print(f"Complete\n{len(DATABASE) - lastDatabaseSize} new zip files catalogued\n")
        lastDatabaseSize = len(DATABASE)
        SOURCESi += 1
    
    print("Saving database...")

    with open("db.json", "w") as fp:
        json.dump(DATABASE, fp)

# CLI entrypoint (defined in setup.py)
def cli():
    global LASTDIR, MDL_PATH

    # For code brevity I use relative paths for configuration files.
    # Save the last working directory for later, to restore before exit.
    LASTDIR = os.getcwd()

    # Configuration files are kept in ~/.mame-dl
    
    MDL_PATH = os.path.expanduser("~/.mame-dl")

    # Make the folder if it doesn't exist
    if not os.path.exists(MDL_PATH):
        os.mkdir(MDL_PATH)
    
    os.chdir(MDL_PATH)

    # initialize DATABASE (zip name to URL mapping) as empty just in case
    global DATABASE
    DATABASE = {}

    parser = argparse.ArgumentParser(
        prog='mame-dl',
        description='CLI ROM manager for MAME',
        epilog='mame-dl v0.1, by zulc22, 2023, 0BSD. Not affiliated in any way with MAME or mamedev.org.'
    )

    operation = parser.add_subparsers(dest='operation')

    ### $ mame-dl add ###
    op_add = operation.add_parser(
        "add",
        help='Download ROMs'
    )
    # ... syntax
    op_add.add_argument(
        "machines", action='store', type=str, nargs='+',
        help='Machine names'
    )
    op_add.add_argument(
        "--force","-F", action="store_true",
        help='Forcefully redownload existing ROMs'
    )
    ### $ mame-dl del ###
    op_add = operation.add_parser(
        "del",
        help='Delete ROMs'
    )
    # ... syntax
    op_add.add_argument(
        "machines", action='store', type=str, nargs='+',
        help='Machine names'
    )
    ### $ mame-dl update ###
    op_update = operation.add_parser(
        "update",
        help='Scrape ROM URLs from sources and rebuild database'
    )
    ### $ mame-dl search ###
    op_search = operation.add_parser(
        "search",
        help='Search ROM names (not machine names or metadata)'
    )
    # ... syntax
    op_search.add_argument(
        "query"
    )
    op_search.add_argument(
        "--regex","-r", action="store_true",
        help="Search with regex pattern instead of string"
    )
    ### $ mame-dl config ###
    op_config = operation.add_parser(
        "config",
        help='Configuration options. Valid keys: mamedir'
    )
    # ... syntax
    op_config.add_argument("key")
    op_config.add_argument("value")

    args = parser.parse_args()

    if args.operation is None:
        # try to load the configuration to show a warning if it doesn't exist yet
        loadConfig()
        parser.parse_args(["--help"]) 
        exitpath()
    
    elif args.operation == "config":
        cli_config(args)
        exitpath()

    elif args.operation == "del":
        cli_del(args)
        exitpath()

    elif args.operation == "add":
        cli_add(args)
        exitpath()

    elif args.operation == "search":
        cli_search(args)        
        exitpath()

    elif args.operation == "update":
        cli_update(args)
        exitpath()
