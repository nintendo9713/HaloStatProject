from bs4 import BeautifulSoup
import requests, re, csv, time
from collections import Counter 
import numpy as np
import sys
import os.path

'''
@TODO - Multiple Gamerags - but must support individual outputs for part 2 to work well

 - Will assume if the file exists, it's accurate
if (gamertag_game_ids.txt exists - skip first part.
then populate game_ids from file.

'''

# Step 1 - Acquire all Game IDs by parsing the players page until the end.
# Step 2 - Store all Game IDs in a file so it never has to be taken again
# Step 3 - Use each Game ID to download the available data into a structure

''' Must Complete '''
root_directory = "C:\\Users\\Jesse\\Documents\\Halo2StatsData\\"

debug = False

sys.path.append(root_directory)

# if not avaialable offline - download a local copy
download_offline = False

# if available offline - parse that file instead
read_offline = False

confirmation = 'n'

# TruthTakesALL1 is a gamertag with very few games to test...
gamertag = "Agnt 007"

game_ids = []

total_games = 0

#while confirmation == 'n':
#    gamertag = input('Enter Gamertag: ')

#    confirmation = input('\nAre you sure you want to run with ' + gamertag + '? (y/n): ')

# root URL - let bs4 do it's thing
URL = 'https://halo.bungie.net/stats/PlayerStatsHalo2.aspx?player='+gamertag

soup = []
# assume it is not available locally / offline
offline = False

if not os.path.exists(root_directory + gamertag + "_game_ids.txt"):
    print("File doesn't exist...buckle up.")

    # overwrite URL if a local copy is available
    if read_offline is True:
        try:
            f = open(root_directory + "\\game_repo\\" + gamertag + "_page_" + "1.html")
            URL = root_directory + "\\game_repo\\" + gamertag + "_page_" + "1.html"
            offline = True
            if debug is True:
                print("## DEBUG ## - Page 1 was available locally...")
        except IOError:
            if debug is True:
                print("Offline copy unavailable - downloading...")
    else:
        if debug is True:
            print("__DEBUG__ - Not available offline - requesting from webpage")
            
        
    # Assign "soup" as the local page or Bungie's page
    if offline is True:
        soup = BeautifulSoup(open(URL), 'html.parser')
    else:
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, 'html.parser')
            
    # don't ask - just took the closest field to the total games
    total_games = soup.find("div", {"class": "rgWrap rgInfoPart"}).get_text("|", strip=True).split('|')[0]
       
    # Regardless of where "soup" came from - convert it to a string as page_source
    page_source = str(soup)

    # get total number of game pages
    try:
        last_page = soup.find('a', {'title':'Last Page'})['href']
    except TypeError:
        pass
        
    print('Number of pages to get for gamertag ' + gamertag + ': ' + last_page.partition("ChangePage=")[2]+'\n')
    total_pages = int(last_page.partition("ChangePage=")[2])

    # Loop through every page of games and add the URL of each game (25 per page) to list
    for i in range(1,total_pages+1):  

        print('Getting games on page ' + str(i) + ' of ' + str(total_pages))
        
        URL = 'https://halo.bungie.net/stats/playerstatshalo2.aspx?player='+gamertag+'&ctl00_mainContent_bnetpgl_recentgamesChangePage=' + str(i)
        # assume page is not available locally from a previous run
        offline = False
        
        # overwrite URL if a local copy is available
        try:
            f = open(root_directory + "\\game_repo\\" + gamertag + "_page_" + str(i) + ".html")
            URL = root_directory + "\\game_repo\\" + gamertag + "_page_" + str(i) + ".html"
            offline = True
            if debug is True:
                print("## DEBUG ## - Page " + str(i) + " was available locally...")
        except IOError:
            if debug is True:
                print("Offline copy unavailable - downloading...")
        
        soup = []
        
        if offline is True:
            soup = BeautifulSoup(open(URL), 'html.parser')
        else:
            page = requests.get(URL)
            soup = BeautifulSoup(page.content, 'html.parser')
            
        page_source = str(soup)
            
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            if '/Stats/' in href:
                # 34 is the magic number to start at the Game ID
                game_id = href[34:href.find('&')]
                # truncate once it's not the number anymore
                
                game_ids.append(game_id)

    # Remove duplicates, I don't know why there are duplicates but this results in the same amount of games as bungie.net shows ¯\_(ツ)_/¯
    game_ids = list(dict.fromkeys(game_ids))

    # If the first entry is not all digits, it's a clan and needs to be purged / popped
    if not game_ids[0].isdigit():
        if debug is True:
            print("## DEBUG ## - Removing clan from game IDs for " + gamertag) 
        game_ids.pop(0)
        
    # Write Game IDs to file
    with open(root_directory + gamertag + "_game_ids.txt", 'w') as game_id_file:
        for i in game_ids:
            game_id_file.write(i+'\n')

# If the file exists, then copy all the game IDs into it...
else:
    print("Game ID file already exists in:")
    print("  " + root_directory + gamertag + "_game_ids.txt")
    print("Reading Game ID's from it")
    # Read Game IDs to file
    with open(root_directory + gamertag + "_game_ids.txt", 'r') as game_id_file:
        content = game_id_file.readlines()
    game_ids = [x.strip() for x in content]
    total_games = len(game_ids)
   
print("Processing games for: " + gamertag)


# This file is the input for the Halo2_StatParser.py program
raw_output_file = open(root_directory + gamertag + "_raw_data.txt", "w")

# global game counter
game_count = 0

# For every game_id, parse for available data
for game_id in game_ids:
    
    game_id = game_id.strip()
    game_count = game_count + 1
    
    print("[" + gamertag + "] Processing Game # " + str(game_count).rjust(6) + " of ~" + str(total_games) + " games || Game ID: " + game_id.rjust(9))
    
    # set URL to online game_id
    URL = "http://halo.bungie.net/Stats/GameStatsHalo2.aspx?gameid=" + game_id
    # assume game is not available offline
    offline = False
    
    if read_offline is True:
        # overwrite URL if a local copy is available
        try:
            f = open(root_directory + "\\game_repo\\" + str(game_id) + ".html")
            URL = root_directory + "\\game_repo\\" + str(game_id) + ".html"
            offline = True
            if debug is True:
                print("## DEBUG ## - " + str(game_id) + " was available locally...")
        except IOError:
            if debug is True:
                print("Offline copy unavailable - downloading...")
    
    if offline is True:
        soup = BeautifulSoup(open(URL), 'html.parser')
    else:
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, 'html.parser')
    

    page_source = str(soup)
  
    ''' Parse Individual Games Here '''
    
    summary = soup.find("ul", {"class":"summary"})
    summary = summary.get_text("|",strip=True).split('|')
    # Since 'Length' was purged from Bungie, replace with 'Ranked' or 'Unranked' if an ExpBar is present
    if (soup.find("div", {"class": "ExpBarText"}) == None):
        summary[3] = 'Unranked'
    else:
        summary[3] = 'Ranked'
    
    # This points to the carnage report table
    carnage_report = soup.find_all("div", {"id":"ctl00_mainContent_bnetpgd_pnlKills"})
    # Apply some strips and splits
    carnage_report = carnage_report[0].get_text("|",strip=True).split('|')
    
    # Write this structure 
    raw_output_file.write("[" + str(game_id) + "]|")
    # No need for "[]" since the list will print them
    raw_output_file.write(str(summary)+ "|")
    raw_output_file.write(str(carnage_report))
    raw_output_file.write('\n')
    
# Close the file
raw_output_file.close()

# Move on to Halo2_StatParser.py
print("Done.")