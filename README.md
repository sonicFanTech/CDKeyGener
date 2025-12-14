# CDKeyGen (CD Key Generator)

A fast Python tool for generating lots of CD Keys for custom installers — without spending hours typing them by hand.

Generate thousands of keys quickly  
Custom key length (default: 25)  
Optional grouping (example: `AAAAA-BBBBB-CCCCC-...`)  
Pattern mode (example: `XXXXX-XXXXX-XXXXX`)  
Unique keys (no duplicates by default)  
One program with **GUI + CLI** modes

---

## Features

- **Bulk generation**: choose how many keys you want
- **Custom key length**: default is 25 characters
- **Grouping support**: split keys into groups (ex: 5 chars each) with a separator
- **Pattern support**: use `X` as random slots, keep everything else literal
- **Unique keys**: prevents duplicates (recommended)
- **Alphabet control**
  - Default avoids confusing characters: `0 O 1 I L`
  - Option to allow ambiguous characters if you want

---

## Requirements

- Python 3.8+ (recommended: 3.10+)
- No external libraries required for the GUI (uses built-in `tkinter`)

> On Windows, `tkinter` is usually included with Python.

---

## Usage

### GUI Mode
- If you compile as a **windowed EXE**, double-clicking will open the GUI automatically.
- You can also force GUI mode from the command line:

bat:
CDKeyGener.exe --GUI


CLI Mode (basic)
Generate 100 keys (length 25) and save to a text file:

python CDKeyGener.py --count 100 --length 25 --out keys.txt


Add grouping (5 characters per group, separated by -):

python CDKeyGener.py --count 100 --length 25 --groupsize 5 --sep - --out keys.txt

Pattern Mode
Use X as random characters:

python CDKeyGener.py --count 50 --pattern "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX" --out keys.txt

Interactive CLI Menu

Run the interactive CLI menu (prompts you for options):

python CDKeyGener.py --CLIinter

Output Formats
You can export keys as:

txt (default)

csv
json

Examples:

python CDKeyGener.py --count 100 --out keys.csv --format csv
python CDKeyGener.py --count 100 --out keys.json --format json

CLI Options:
Run this anytime to see all options:

python CDKeyGener.py --help

Common options:

--count → how many keys
--length → key length (ignored if using --pattern)
--pattern → pattern using X for random characters
--groupsize → group size for auto grouping (like 5)
--sep → grouping separator (default -)
--out → output file
--format → txt / csv / json
--GUI → force GUI mode
--CLIinter → interactive CLI mode


Building an EXE (PyInstaller)
Windowed EXE (GUI on double-click)
pyinstaller --onefile --windowed CDKeyGener.py --name CDKeyGen

Console EXE (CLI by default)
pyinstaller --onefile CDKeyGener.py --name CDKeyGen_CLI


Both builds still support --GUI and --CLIinter
