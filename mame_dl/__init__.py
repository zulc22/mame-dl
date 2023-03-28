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

def cli():

    LASTDIR = os.getcwd()
    MDL_PATH = os.path.expanduser("~/.mame-dl")
    if not os.path.exists(MDL_PATH):
        os.mkdir(MDL_PATH)
    os.chdir(MDL_PATH)
    global DATABASE
    DATABASE = {}

    def exitpath():
        os.chdir(LASTDIR)
        exit()
    
    def loadDatabase():
        if not os.path.exists("db.json"):
            print("No database! Run 'mame-dl update' to generate it.")
            exitpath()
        with open("db.json") as fp:
            global DATABASE
            DATABASE = json.load(fp)
    
    def loadConfig():
        global CONFIG
        if os.path.exists("conf.json"):
            with open("conf.json") as fp:
                CONFIG = json.load(fp)
        else:
            print("Configuration required!\n"+
                "Set the MAME install directory with 'mame-dl config mamedir [PATH]'.")
            exitpath()
    
    def saveConfig(k,v):
        global CONFIG
        if os.path.exists("conf.json"):
            if 'CONFIG' not in globals():
                with open("conf.json") as fp:
                    CONFIG = json.load(fp)
            CONFIG[k] = v
            with open("conf.json","w") as fp:
                json.dump(CONFIG, fp)
        else:
            CONFIG = {k: v}
            with open("conf.json","w") as fp:
                json.dump(CONFIG, fp)

    parser = argparse.ArgumentParser(
        prog='mame-dl',
        description='CLI ROM manager for MAME',
        epilog='mame-dl v0.1, by zulc22, 2023, 0BSD. Not affiliated in any way with MAME or mamedev.org.'
    )

    operation = parser.add_subparsers(dest='operation')

    op_add = operation.add_parser("add", help='Download ROMs')
    op_add.add_argument("machines", action='store', type=str, nargs='+', help='Machine names')
    op_add.add_argument("--force","-F", help='Forcefully redownload existing ROMs', action="store_true")

    op_add = operation.add_parser("del", help='Delete ROMs')
    op_add.add_argument("machines", action='store', type=str, nargs='+', help='Machine names')

    op_update = operation.add_parser("update", help='Scrape ROM URLs from sources and rebuild database')

    op_search = operation.add_parser("search", help='Search ROM names (not machine names or metadata)')
    op_search.add_argument("query")
    op_search.add_argument("--regex","-r", help="Search with regex pattern instead of string", action="store_true")

    op_config = operation.add_parser("config",
        help='Configuration options. Valid keys: mamedir')
    op_config.add_argument("key")
    op_config.add_argument("value")

    args = parser.parse_args()

    if args.operation is None:

        loadConfig()
        parser.parse_args(["--help"])
        exitpath()
    
    elif args.operation == "config":
        
        if args.key == "mamedir":
            os.chdir(LASTDIR)
            directory = os.path.abspath(args.value)
            os.chdir(MDL_PATH)
            if not os.path.exists(directory):
                print("Invalid directory",directory)
                exitpath()
            if os.path.basename(directory) == "roms":
                directory = os.path.abspath(directory+os.path.sep+"..")
            if directory[-1] != os.path.sep: directory += os.path.sep
            if not os.path.exists(directory+"roms"):
                print("That path exists, but it isn't a 'roms' directory, nor does it contain one.\n"+
                    "Are you sure you specified a path to a MAME installation?")
                exitpath()
            print("Set successfully to",directory)
            saveConfig("mamedir", directory)
        else:
            print("Unknown config option",args.key)

        exitpath()

    elif args.operation == "del":

        loadConfig()

        for m in args.machines:
            zip = CONFIG['mamedir'] + os.path.sep + "roms" + os.path.sep + m + ".zip"
            if os.path.exists(zip):
                os.unlink(zip)
            else:
                print(f"- '{m}' doesn't exist in the roms directory, silly!")
                exitpath()

    elif args.operation == "add":
        
        loadConfig()
        loadDatabase()
        
        for m in args.machines:
                
            zip = m if m.endswith(".zip") else m+".zip"

            if zip not in DATABASE:
                print(f"- No such machine '{m}' was found.")
                exitpath()

            path = os.path.join(CONFIG['mamedir'], "roms", zip)
            if os.path.exists(path):
                if args.force: os.unlink(path)
                else:
                    print(f"- '{m}' already exists in the roms directory, silly!")
                    continue

            if os.path.exists(path+".tmp"):
                os.unlink(path+".tmp")

            os.chdir(CONFIG['mamedir']+os.path.sep+"roms")

            subprocess.run([
                "wget",
                "-q","--show-progress","--progress=bar:force:noscroll",
                "-O",zip+".tmp",
                DATABASE[zip]
            ])

            os.rename(zip+".tmp", zip)

        exitpath()

    elif args.operation == "search":

        loadDatabase()

        if args.regex:
            for i in DATABASE:
                i = i[:-4]
                if re.match(args.query, i):
                    print(i)
        else:
            for i in DATABASE:
                i = i[:-4]
                if args.query in i:
                    print(i)
        
        exitpath()

    elif args.operation == "update":

        if not os.path.exists("sources.cfg"):
            print("No sources.cfg file, writing defaults\n")
            with open('sources.cfg', 'w') as fp:
                fp.write(defaultsources.DEFAULTSOURCES)

        with open('sources.cfg') as fp:
            SOURCES = [i[:-1] if i.endswith('\n') else i for i in fp.readlines()]
        
        SOURCESlen = len(SOURCES)
        SOURCESi = 1

        DATABASE = {}
        lastDatabaseSize = 0

        for link in SOURCES:
            print(f"Source {SOURCESi} of {SOURCESlen}: {link}")
            print("Requesting...",end=' '); sys.stdout.flush()
            page = requests.get(link)
            page.raise_for_status()
            print("Parsing...",end=' '); sys.stdout.flush()
            pagesoup = BeautifulSoup(page.content, "html.parser")
            for e in pagesoup.find_all('a'):
                if e.string and e.string.endswith(".zip") and e.string not in DATABASE:
                    DATABASE[e.string] = urllib.parse.urljoin(link+"/", e.get('href'))
            print(f"Complete\n{len(DATABASE) - lastDatabaseSize} new zip files catalogued\n")
            lastDatabaseSize = len(DATABASE)
            SOURCESi += 1
        
        print("Saving database...")

        with open("db.json", "w") as fp:
            json.dump(DATABASE, fp)
        
        exitpath()