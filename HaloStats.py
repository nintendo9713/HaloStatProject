from bs4 import BeautifulSoup
import requests, re, csv, time
from collections import Counter 
import numpy as np
import sys, os.path
from tkinter import *
import tkinter.filedialog
import tkinter.messagebox

import threading

import datetime   
import ast
import calendar
from operator import itemgetter

'''
Anaconda - pyinstaller --onefile HaloStats.py
exec(open("C:\\Users\\Jesse\\Documents\\Halo2StatsData\\HaloStats.py").read())
'''

# Maybe this will help someone.
readme_string = """
Halo Stat Downloader 0.1.1.7 - Current build Halo 2 Only\n
Adjust directory if desired.
Put gamertags in the boxes and click download stats (multithreaded)
Be patient, it's taking longer due to server load. 
Once downloaded, you will have a <gamertag>_raw_data.txt file saved. for each
gamertag entered. \n
Now click the PARSE button, and you will have a file generated for
<1st gamertag>_stats.txt.  The file will combine all your gamertags entered
to a single stat breakdown.\n
I hope it works well for you.\n
**Currently - Compare stats not working**
"""
# default root directory - can be changed in GUI
'''
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
'''    

#root_directory = "C:/" #os.path.expanduser("~")
root_directory = "C:/Users/Jesse/Documents/Halo2StatsData"

#global status string
status = "Nothing happening"

# Clock is ticking - making it global            
# List of gameid's for each tag to be written to a file
game_ids = []
            

# Used for games actually purged, but not implemented
purged_games = 0
bad_requests = 0
attempt_limit = 10
attempts = 0

# Parallel stuff
page_threads = []

def updateGlobalStatus(update):
    global status
    print(update)
    status = update
    
def browseDirectory(root_entry):
    global root_directory
    root_directory = tkinter.filedialog.askdirectory()
    root_entry.delete(0,END)
    root_entry.insert(0,root_directory)
    
# Launch separate thread so GUI doesn't freeze
def threadButtonDownload(gt_entries):

    global root_directory
    sys.path.append(root_directory)
    
    # Try to write a 1 Byte dummy file to make sure, because I once ran a 6 hour download that then tried to write, failed, and it ruined my day.
    try:    
        test_file = open(root_directory + "/test.txt", "w")
        test_file.write("stat test - ignore / delete")
    except:
        print("No write permissions, change your download destination|| " + root_directory + "/test.txt")
        tkinter.messagebox.showerror(title="Error", message="No write permissions, change your download destination.")
        return
    
    gamertags = [e.get() for e in gt_entries]
    
    if not gamertags:
        s = "No gamertags entered..."
        updateGlobalStatus(s)
        return
        
    # if we do have gamertags, let each one run in a thread for maximum power
    for gamertag in gamertags:
        threading.Thread(target=downloadStats, args=(gamertag,)).start()
        
def downloadStatPage(gamertag, pageNumber):
    global game_ids
    # This is my error check for 404s for pages.
    while True:
    
        URL = 'https://halo.bungie.net/stats/playerstatshalo2.aspx?player=' + gamertag + '&ctl00_mainContent_bnetpgl_recentgamesChangePage=' + str(pageNumber)
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, 'html.parser')
        page_source = str(soup)
        
        # My attempt to fix 404 errors for pages. If we made it past the landing page, no going back. INFINITE reattempts.
        # Compare 'currentPage' to i and make sure they match, because if a page errors, it -can- go to the landing page (page 1)
        # Hopefully this will catch a 404 error as there won't be a tag for "currentPage" if it just displays "something's broken...
        p = soup.find('a', {'class':"rgCurrentPage"}).text

        # Reset loop if failed...
        if p != str(pageNumber):
            print("page failed to load, trying again...")
            continue
        
        # Grab every link on the page, and if it has "/Stats/", it's a link to a game
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            if '/Stats/' in href:
                # 34 is the magic number to start at the Game ID, and truncate once it's not the number anymore
                game_id = href[34:href.find('&')]
                
                # Append the game_id to the list
                # List appending is proven thread safe! - stack overflow...
                game_ids.append(game_id)
        break

def downloadStats(gamertag):
  
    validateTags(gamertag)
    
    header = "[" + gamertag + "] "
    
    if gamertag.strip():
        print(header.ljust(19) + "Generating stats")
        s = root_directory + "/" + gamertag + "_raw_data.txt"
        if os.path.exists(s):
            print("This popup is because I once erased a 14k game file that took hours to download, and I'm only trying to help...")
            tkinter.messagebox.showerror(title="Error", message="File: " + s + " already exists.\n\nManually backup or remove file.")
            return
        else:
            print("Writing to " + s)

            # root URL - let bs4 do it's thing
            for attempt in range(attempt_limit):
                print(header.ljust(19) + "Attempting #" + str(attempt+1) + " out of " + str(attempt_limit) + " to get main stat page. ")
                try:
                    URL = 'https://halo.bungie.net/stats/PlayerStatsHalo2.aspx?player='+gamertag
                    soup = []
                    page = requests.get(URL)
                    soup = BeautifulSoup(page.content, 'html.parser')
                    
                    page_source = str(soup)

                    # don't ask - just took the closest field to the total games
                    total_games = soup.find("div", {"class": "rgWrap rgInfoPart"}).get_text("|", strip=True).split('|')[0]
                
                    # get total number of game pages
                    last_page = soup.find('a', {'title':'Last Page'})['href']
                except:
                    print(header.ljust(19) + "Likely 404 error. Let's get it another go.")
                else:
                    break
            else:
                # Failing all attempts - real bad luck....
                print(header.ljust(19) + "Bungie ain't having it, sorry. Try again in a minute...")
                return
                    
                # All these confusing tidbits are bruteforced because I don't know what I'm doing
            updateGlobalStatus(header.ljust(19) + 'Number of pages to get: ' + last_page.partition("ChangePage=")[2]+'\n')
            total_pages = int(last_page.partition("ChangePage=")[2])    
                
            global page_threads
            # Loop through every page of games IN PARALLEL! and add the URL of each game (25 per page) to list
            for i in range(1,total_pages+1):  
            
                my_thread = threading.Thread(target=downloadStatPage, args=(gamertag,i,))
                page_threads.append(my_thread)
                my_thread.start()
                
            # Hold the line until ALL game IDs have been appended.
            for t in page_threads:
                t.join()
            
            print(header.ljust(19) + "All games scraped from pages, downloading games.")
            #updateGlobalStatus(header.ljust(19) + 'Getting games on page ' + str(i) + ' of ' + str(total_pages))
                
                
            global game_ids            
            # Remove duplicates, I don't know why there are duplicates but this results in the same amount of games as bungie.net shows ¯\_(ツ)_/¯
            game_ids = list(dict.fromkeys(game_ids))
            
            # If the first entry is not all digits, it's a clan and needs to be purged / popped
            if not game_ids[0].isdigit():
                print(header.ljust(19) + "## DEBUG ## - Removing clan from game IDs.") 
                game_ids.pop(0)
                
            # Write Game IDs to file
            with open(root_directory + "/" + gamertag + "_game_ids.txt", 'w') as game_id_file:
                for i in game_ids:
                    game_id_file.write(i+'\n')
                    
            updateGlobalStatus(header.ljust(19) + "Processing games")
                    
                    
            # This file is the input for the Halo2_StatParser.py program
            raw_output_file = open(s, "w")

            # Game counter
            game_count = 1

            # Keep iterating through game_ids until they don't error out...
            while (game_ids):

                # For every game_id, parse for available data
                for game_id in game_ids:
                    game_id = game_id.strip()
                    
                    updateGlobalStatus(header.ljust(19) + str(len(game_ids)).rjust(5) + " games left to download || Game ID: " + game_id.rjust(9))
                        
                    # set URL to online game_id
                    URL = "http://halo.bungie.net/Stats/GameStatsHalo2.aspx?gameid=" + game_id
                    page = requests.get(URL)
                    soup = BeautifulSoup(page.content, 'html.parser')
                    page_source = str(soup)
                    
                    # Parse Individual Games Here
                    try:
                        summary = soup.find("ul", {"class":"summary"})
                        summary = summary.get_text("|",strip=True).split('|')
                        # Since 'Length' was purged from Bungie, replace with 'Ranked' or 'Unranked' if an ExpBar is present
                        if (soup.find("div", {"class": "ExpBarText"}) == None):
                            summary[3] = 'Unranked'
                        else:
                            summary[3] = 'Ranked'
                    except:
                        print(header.ljust(19) + "Got a bad request...putting it back at bottom of list to try later...")
                        global bad_requests
                        bad_requests = bad_requests + 1
                        continue
                    
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
                    
                    # If it made it this far, we're good.
                    game_ids.remove(game_id)
                    game_count = game_count + 1
            
            updateGlobalStatus(header.ljust(19) + "Done downloding games. " + str(bad_requests) + " bad requests that had to be re-downloaded. Ready to parse.")

# TODO                            
def validateTags(gamertags):
    return


# Launch separate thread so GUI doesn't freeze
def threadButtonParse(gt_entry):
    threading.Thread(target=parseStats, args=(gt_entry,)).start()
    

def parseStats(gt_entries):
    gamertags = [e.get() for e in gt_entries]
    s = "Parsing " + ','.join(gt for gt in gamertags if gt.strip()) + " stats... (shouldn't take more than 5 seconds)"
    updateGlobalStatus(s)
    
    # @TODO - Pass "Compare Stats entries and populate
    vs_gamertag = []
    
    gamertag = list(filter(None, gamertags))
    
    if not gamertag[0]:
        updateGlobalStatus("No gamertags entered. Try again.")
    
    # Output file
    global root_directory
    output_file_name = root_directory + "/" + gamertag[0] + "_stats.txt"
    output_file = open(output_file_name, "w")
    
    for gt in gamertag:
        # Writes the URLs for each gamertag at the top of the file
        output_file.write("https://halo.bungie.net/stats/PlayerStatsHalo2.aspx?player=" + gt + "\n")
    
    # Player K/D/A's for specific game categories.  If you think of more, AIM me @dane_cook_89
    player_stats_global         = np.zeros((3,), dtype=int)
    player_stats_customs        = np.zeros((3,), dtype=int)
    player_stats_ranked         = np.zeros((3,), dtype=int)
    player_stats_clan           = np.zeros((3,), dtype=int)
    player_stats_ranked_no_clan = np.zeros((3,), dtype=int)
    player_stats_ranked_ffa     = np.zeros((3,), dtype=int)
    player_stats_ranked_team    = np.zeros((3,), dtype=int)
    player_stats_matchmaking    = np.zeros((3,), dtype=int)

    # Head to Head ™ Beta...
    head_to_head_player   = np.zeros((3,), dtype=int)
    head_to_head_opponent = np.zeros((3,), dtype=int)
    head_to_head_games = 0

    # (wins, losses, rate)
    ranked_win_rate = (np.zeros((3,), dtype = float))
    
    # This is the list that will populate with game structures from the raw data files generated    
    global_stats = []
    
    # List of players to count frequency
    players = []

    # List of official teams to check against - & yes - if somebody has this as a gamertag, it might break this entire operation
    team_list = ['Red Team','Blue Team','Green Team','Yellow Team','Orange Team','Purple Team','Pink Team','Brown Team']

    # Keep highest rank and the associated game_id
    max_rank_overall = [0, 0]
    max_rank_no_clan = [0, 0]

    # Stolen from Stack Overflow
    # Converts dictionary to string
    # @TODO - add formatting - left / right justify & New line fix in file output
    def dict_to_string(d):
      return str(d).replace(', ','\n\r').replace("u'","").replace("'","")[1:-1]

    # Stolen from Stack Overflow
    # Returns key with max value in a dictionary
    def key_with_max_value(d):
         v = list(d.values())
         k = list(d.keys())
         return k[v.index(max(v))]

    # Husker's famous dictionary insert. All rights reserved by him.
    def dictionary_insert(key, dictionary):
        if key in dictionary:
            # Increment count of word by 1 
            dictionary[key] = dictionary[key] + 1
        else:
            # Add the word to dictionary with count 1 
            dictionary[key] = 1

    # My horrible manual way of adding 2 hours for PST - CST and adjusting AM / PM
    def adjust_time(time):
        # Get the hour as an integer
        hour = int(time.split(':')[0])
        # AM --> PM --> AM
        if hour in ['10','11']:
            if time.split()[1] == 'PM':
                time = time.split()[0] + ' AM ' + time.split()[2]
            else:
                time = time.split()[0] + ' PM ' + time.split()[2]
            #print("#2.5 - " + time)
        
        # Move ahead 2 hours
        hour = hour + 2
        # Adjust hours
        if hour > 12:
            hour -= 12
        # For single digit hours, append a space before it to maintain a clean dictionary
        if hour < 10:
            hour = ' ' + str(hour)
        # Rebuild string
        time = str(hour) + ':' + time.split(':')[1]

        # Concatenate the hour and AM/PM
        time = time.split(':')[0] + " " + time.split()[1]
        
        return time

          
    # Used for a time dictionary - number of games played at certain hours
    # @TODO - fix dict output and remove unnecessary logic for adding a space before. it's gross.
    def init_clock_dictionary():
        return {\
            ' 1 AM': 0, \
            ' 2 AM': 0, \
            ' 3 AM': 0, \
            ' 4 AM': 0, \
            ' 5 AM': 0, \
            ' 6 AM': 0, \
            ' 7 AM': 0, \
            ' 8 AM': 0, \
            ' 9 AM': 0, \
            '10 AM': 0, \
            '11 AM': 0, \
            '12 PM': 0, \
            ' 1 PM': 0, \
            ' 2 PM': 0, \
            ' 3 PM': 0, \
            ' 4 PM': 0, \
            ' 5 PM': 0, \
            ' 6 PM': 0, \
            ' 7 PM': 0, \
            ' 8 PM': 0, \
            ' 9 PM': 0, \
            '10 PM': 0, \
            '11 PM': 0, \
            '12 AM': 0, \
            }

    # Used for a weekday dictionary - number of games played at certain hours
    def init_weekday_dictionary():
        return {\
            'Sunday': 0, \
            'Monday': 0, \
            'Tuesday': 0, \
            'Wednesday': 0, \
            'Thursday': 0, \
            'Friday': 0, \
            'Saturday': 0, \
            }
            
    def init_team_color_dictionary():
        return {\
            'Red Team': 0, \
            'Blue Team': 0, \
            'Green Team': 0, \
            'Yellow Team': 0, \
            'Pink Team': 0, \
            'Brown Team': 0, \
            'Purple Team': 0, \
            'Orange Team': 0, \
            }
            
    def init_month_dictionary():
        return {\
            'January': np.zeros((4,), dtype=float), \
            'February': np.zeros((4,), dtype=float), \
            'March': np.zeros((4,), dtype=float), \
            'April': np.zeros((4,), dtype=float), \
            'May': np.zeros((4,), dtype=float), \
            'June': np.zeros((4,), dtype=float), \
            'July': np.zeros((4,), dtype=float), \
            'August': np.zeros((4,), dtype=float), \
            'September': np.zeros((4,), dtype=float), \
            'October': np.zeros((4,), dtype=float), \
            'November': np.zeros((4,), dtype=float), \
            'December': np.zeros((4,), dtype=float), \
            }
            
    ''' Global Counters / Data Aggregators '''
    # Create an empty dictionary 
    map_dictionary = dict() 
    map_kd_dictionary = dict()
    date_dictionary = dict() 
    time_dictionary = init_clock_dictionary()
    weekday_dictionary = init_weekday_dictionary()
    game_type_dictionary = dict()
    playlist_dictionary = dict()
    team_color_customs_dictionary = init_team_color_dictionary()
    team_color_ranked_dictionary = init_team_color_dictionary()
    team_color_dictionary = init_team_color_dictionary()
    clans_dictionary = dict()

    ## DEBUG ##
    monthly_kda_dictionary = init_month_dictionary()
    ## DEBUG ## \end

    # The big one....every player played with counted
    player_dictionary = dict()

    # Specific Game Counters
    ranked_games = 0
    ranked_team_games = 0
    ranked_ffa_games = 0
    unranked_games = 0
    unranked_team_games = 0
    unranked_ffa_games = 0
    custom_games = 0
    custom_team_games = 0
    custom_ffa_games = 0
    clanmatch_games = 0
    clanmatch_games_minor = 0
    clanmatch_games_major = 0


    def process_carnage_report(carnage_report, playlist, is_ranked):

        ''' Build a uniform carnage report '''
        
        # There are 7 types of games:
        #   [1] - Clan Match
        #   [2] - Matchmaking Ranked Team
        #   [3] - Matchmaking Unranked Team
        #   [4] - Matchmaking Ranked Free-for-All
        #   [5] - Matchmaking Unranked Free-for-All
        #   [6] - Custom Team Game
        #   [7] - Custom Free-for-All
        #
        #  The <header>, aka top row, is always:
        #
        #        ['Players', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score']
        #
        #  This works fine in unranked, as all <player> rows perfectly represent this.  You can reshape the list into an 8 wide array as such:
        #    
        #      np.array(carnage_report).reshape(int(len(carnage_report)/8),8)
        #
        #  For an unranked team game, there will also be an 8 element wide row for each team, such as 'Red Team' or 'Blue Team'.  This is why a list of all teams 
        #    are available to check against.  If it is the team row, until you hit another team row, every player beneath is on that.
        #
        #  If a game is ranked - the header is the same, but now all player rows have the following fields:
        #
        #        ['Players', 'Rank', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score']
        #  
        #  Rank will be a # from 1 to 50.  This algorithm makes every carnage report into a 9 element wide row.  The header is easily done with a ".insert(1, 'Rank').
        #    
        #  In an unranked game, you can easily iterate through the list and at every 9 elements, insert a '-'.  Simply a placeholder to disregard.  This is done for
        #    both Team and Free-for-All unranked games.
        #
        #  For a ranked game - either Team or Free-for-All, simply inserting 'Rank' at index [1] is sufficient to create the 9 element wide carnage report since each 
        #    player will already have an actual number as a rank in that element.
        #
        #  The same logic for 'Red Team' / 'Blue Team' (checking against a list) applies for both Ranked and Unranked, as a rank does not appear in a Team row, but you
        #    can't blindly enter a "-" at every 9 indices because the players now have a rank. This is solved by iterating backwards, and if the element is found in the
        #    team_list variable (a default team in Halo 2), then a '-' is inserted after to make the Team rows 9 elements wide.
        #
        #  Finally, as if that wasn't enough - These are ranked, and there is a flag that verifies the game was a clan match, but instead of saying 'Red Team' and 
        #    'Blue Team', it's the clan named by a 12 year old. These are indiscernible from an Xbox Live gamertag since they have the same requirements.  Because the 
        #    players have a 9 element wide row, clan rows do not, and each field will never have an alphabet character - starting at the 5th row, or index [45], check
        #    8 elements ahead.  If it has an alphabetical character, it must be a clan row since 8 elements ahead of every character will not possess an alphabetical
        #    character.  For easier processing, a '*' is inserted following the clan name as opposed to '-'.
        #
        #  Implementing all of these scenarios will result in a 9 element wide 2D array of the games carnage report for easy processing.
            
        # Handle case where it's a clan match....
        # Clan matches are unique in the sense that instead of 'Red/Blue Team', it's the clan names which are practically indiscernable to an Xbox Live gamertag
        if "Clanmatch" in playlist:
            # Increment total clan games by 1
            nonlocal clanmatch_games
            clanmatch_games += 1
            # Increase the <header> row from 8 to 9
            carnage_report.insert(1, 'Rank')
            # Guaranteed (or your money back) to be the index following the first clan name.
            # @NOTE - A '*' is used instead of '-' to quickly test for a Clan vs. player
            carnage_report.insert(10, '*')
            
            # Start at first gamertag in first clan - always #18 after previous inserts
            # @NOTE - can **PROBABLY** beef this up to 45.  45 would represent header(9) + clan1(9) + gamertag(9)*3 = 45.  The second clan wouldn't be shown until then given clan matches were a minimum of 3
            #       --> but what if someone disconnected and Bungie purged that data?
            i = 45
            while i < len(carnage_report):
                # Checks the element 8 ahead for an a-z/A-Z character
                if bool(re.match('^(?=.*[a-zA-Z])', carnage_report[i+8])) and carnage_report[i+8] != 'N/A':
                    # if so, we're at the clan name
                    #print("Clan name = " + carnage_report[i])
                    # insert accordingly
                    carnage_report.insert(i + 1, '*')
                    break
                # Iterate by 9 to move ahead an entire row to the next gamertag or clan name to test
                i += 9

            # Players determined by dividing by 9.  Then remove the two clan lines and header (-3)
            player_count = int((len(carnage_report) / 9) - 3)
            
            # This is needed due to a few games registered as "Clanmatch" without major/minor - but the size of teams varied
            if player_count <= 8:
                nonlocal clanmatch_games_minor
                clanmatch_games_minor += 1
            else:
                nonlocal clanmatch_games_major
                clanmatch_games_major +=1 
               
            '''
            # Match was uneven
            if player_count % 2 == 1:  
                if debug is True:
                    print("Uneven clan match.")
                    if player_count < 8:
                        print("Hold the phone, we have an uneven Minor Clanmatch")
                
            '''
            
        # If not ranked, each gamertag should be appended with a '-' as a hack
        elif is_ranked is False:
            i = 1
            while i < len(carnage_report):
                carnage_report.insert(i, '-')
                i += 9
            # Always enter the Rank at this position - overwrites the '-'
            carnage_report[1] = 'Rank'
        else:
            carnage_report.insert(1, 'Rank')
            for i in reversed(carnage_report):
                # If entry is a Default Team, insert a '-'
                if i in team_list:
                    carnage_report.insert(carnage_report.index(i) + 1, '-')
        
        #print(carnage_report)
        carnage_report = np.array(carnage_report).reshape(int(len(carnage_report)/9),9) 
        
        return carnage_report     

    # Create a list of all the gamertags' raw_data.txt files     
    raw_data_files = []
    
    # Turn ^ array into a file list
    for gt in gamertag:
        raw_data_files.append(root_directory + "/" + gt + "_raw_data.txt")
    
    for f in raw_data_files:
        try:
            with open(f) as infile:
                local_stats = infile.readlines()
            # Strips all new line characters
            local_stats = [x.strip() for x in local_stats]
            # global_stats holds for ALL gamertags in list, so it "extends" each one so they are all calculated together
            global_stats.extend(local_stats)
        except:
            print("No file found for " + root_directory + "/" + gt  + "_raw_data.txt.  Ignoring..")
            
    # Remove duplicates    
    global_stats = list(set(global_stats))
    
    if not global_stats:
        tkinter.messagebox.showerror(title="Error", message="Stats list empty - Check Gamertags and Files")
        updateGlobalStatus("Nothing happening...")
        return
        
    # Populate the players[] list by truncating the gamertags from the file names
    for i in raw_data_files:
        players.append(i.split(root_directory)[1].split("_raw_data.txt")[0])
    
    # global_stats is now a list of every line from each file in gamertag[]
    total_games = str(len(global_stats))

    print("\n")
    print("Games found: " + total_games)

    ''' BIG PARSER HERE '''
    # each line in global stats has the following layout:
    # [game_id]|['game_type' on 'map', 'playlist', 'date, time', 'un/ranked']|[carnage_report]
    # @TODO - reversed() might not be needed here... check removing duplicates above
    for i in reversed(global_stats):

        # Splits into [0] = game_id, [1] = summary, and [2] = carnage report
        structure = i.split('|')
        
        # Removes the single quotes before and after the game_id and casts as an integer
        game_id = int(structure[0][1:-1])
        
        # Takes the first element of [1], which is the summary, strips the brackets, and splits from the right at " on ".
        # The maxsplit flag is set to 1 to handle the rare game type "2 on 1 on <map>". 
        game_type = structure[1].strip('][').split(', ')[0].rsplit(" on ", maxsplit=1)[0][1:]
        
        # Takes the first element of [1], which is the summary, strips the brackets and takes the last item from the split at " on ".
        map_played = structure[1].strip('][').split(', ')[0].split(" on ")[-1][:-1]
        
        # Takes the first element of [1], which is the summary, stripes
        # @TODO - Make less dangerous - what if empty??
        playlist = structure[1].strip('][').split(', ')[1][12:-1]
        
        # Splits the elements of [1] by ", " after stripping the brackets, takes the 3rd element, and truncates the initial "'"
        date = structure[1].strip('][').split(', ')[2][1:]
        
        # Input the 3 parts of date[] above as integers, and use strftime() to output the day
        # Shamlessly stolen from: https://stackoverflow.com/questions/9847213/how-do-i-get-the-day-of-week-given-a-date/51516223#51516223  
        day = datetime.date(int(date.split('/')[2]), int(date.split('/')[0]), int(date.split('/')[1])).strftime('%A')
        
        # Splits the elements of [1] by ", " after stripping the brackets, takes the 4th element, and truncates the final "'"
        time = adjust_time(structure[1].strip('][').split(', ')[3][:-1])

        # Populate the dictionaries for the games being parsed
        dictionary_insert(map_played, map_dictionary)
        dictionary_insert(date,       date_dictionary)
        dictionary_insert(time,       time_dictionary)
        dictionary_insert(game_type,  game_type_dictionary)
        dictionary_insert(day,        weekday_dictionary)
        dictionary_insert(playlist,   playlist_dictionary)
        
        # Quick read to see if game was marked as Ranked. This assumes Halo2_StatGenerator was correct in its handling of the ExpBar flag
        is_ranked = True if structure[1].strip('][').split(', ')[4][1:-1] == 'Ranked' else False    
        # Clan matches are unique in the sense that instead of 'Red/Blue Team', it's the clan names which are practically indiscernable to an Xbox Live gamertag
        is_clanmatch = True if "Clanmatch" in playlist else False
        # @TODO - Some gamertags still have weird custom games names intact, but it's too few to care. See complete Playlist breakdown for stragglers
        is_custom = True  if playlist == "Arranged Game" else False
        
        # Simple counters
        if is_ranked is True:
            ranked_games += 1 
        else:
            unranked_games += 1 
            
        if is_custom:
            custom_games += 1
            
        # Convert the data string into an actual list
        carnage_report_data = ast.literal_eval(structure[2])

        # Passes in the carnage report as a list, and uses playlist / is_ranked to return a 9 element wide table
        carnage_report = process_carnage_report(carnage_report_data, playlist, is_ranked)

        # These buffers reset for each game. Going down the rows, each is updated accordingly so when the gamertag matches, it can apply the correct team.
        clan_name_buffer = ""
        team_color_buffer = ""
        
        # Assumes true, but if a second default team is hit before the gamertag, then it's a loss.  Meant for ranked only.
        winning_team = True
        
        # Reset to 0,0.  At each team color, flip a value so if the second is false when the gamertag is hit, it's a win.  If it's true, it's a loss. If both are false, it's a FFA
        winning_tracker = [False, False]
        
        # If any Head to Head gamertags is any element of the carnage report - assume it counts
        head_to_head_enabled = True if any(q in vs_gamertag for q in carnage_report_data) else False
        
        
        
        # Iterate through carnage report, ignoring the header row
        for i in carnage_report[1:]:
        
            # If the player name is any of the submitted gamertags, enable
            is_gamertag = True if i[0] in gamertag else False
            
            if is_gamertag and is_clanmatch:
                # Append the latest Clan name and increase by 1
                dictionary_insert(clan_name_buffer, clans_dictionary)
        
            # First and foremost, if a player - add them to the player dictionary
            if i[0] not in team_list and i[1] != '*' and i[0] not in gamertag:
                dictionary_insert(i[0], player_dictionary)
            
            # Head to Head .....
            # If ranked and vs. player is in game, add it.
            if head_to_head_enabled and is_ranked:
                if i[0] in vs_gamertag:
                    kda = list(map(int, i[2:5]))
                    head_to_head_opponent += kda
                    head_to_head_games += 1
                if i[0] in gamertag:
                    kda = list(map(int, i[2:5]))
                    head_to_head_player += kda
                    
             
            # Determines if a clan row
            if i[1] == '*':
                # Update latest clan name as it goes down the list
                clan_name_buffer = i[0]
                
            # @NOTE - CANNOT use if gamertag in - because XBL Guests had gamertag(G)
            # Update all the K/D/A global variables
            if is_gamertag:
                # Convert to a 3 element int array for [Kills, Assists, Deaths]
                # @NOTE - 'kad' seems weird, but 'kda' seems to read better although it's not lined up
                kda = list(map(int, i[2:5]))
                
                # Suicides, Betrayals seem to have been purged... All 0's
                # @TODO Score - Flag? Bomb? TS? Oddball? KOTH?
                # sb = list(map(int, i[6:8]))
                player_stats_global += kda
               
                # Map K/D/A processing
                if map_played in map_kd_dictionary:
                    map_kd_dictionary[map_played][0:3] += kda
                # For the first time a map is played - initialize a 3 element array
                else:
                    map_kd_dictionary[map_played] = np.zeros((4,), dtype=float)
                    map_kd_dictionary[map_played][0:3] += kda
                
                if not is_custom:
                    # If it's not custom, it must but matchmade..
                    player_stats_matchmaking += kda 
                    
                if is_ranked:
                
                    # Retrieve highest level by comparing if the second element is a number (rank)
                    if int(i[1]) > int(max_rank_overall[0]):
                        max_rank_overall[0] = i[1]  
                        max_rank_overall[1] = game_id
                    if not is_clanmatch and int(i[1]) > int(max_rank_no_clan[0]):
                        max_rank_no_clan[0] = i[1]        
                        max_rank_no_clan[1] = game_id
                    
                    # Quirky stat tracking - don't ask #
                    # Add K/D/A to ranked stats
                    player_stats_ranked += kda
                    
                    # If no team color has populated the buffer, it must be a ranked FFA
                    if team_color_buffer == "":
                        player_stats_ranked_ffa += kda
                        ranked_ffa_games += 1
                    # Otherwise, must be a ranked Team Game:
                    else:
                        player_stats_ranked_team += kda
                        ranked_team_games += 1
                        dictionary_insert(team_color_buffer, team_color_ranked_dictionary)
                    
                    # Self documenting...?
                    if is_clanmatch:
                        player_stats_clan += kda
                    else:
                        player_stats_ranked_no_clan += kda
                        
                    
                    # Montly KDA
                    monthly_kda_dictionary[calendar.month_name[int(date.split('/')[0])]][0:3] += kda
                    # Increment total games by one
                    monthly_kda_dictionary[calendar.month_name[int(date.split('/')[0])]][3] += 1
                    
                    # Win Rate processing...
                    if not winning_tracker[0]:
                        # Skip ranked FFA for now...
                        continue
                    # Check second flag for win / loss
                    if not winning_tracker[1]:
                        ranked_win_rate[0] += 1
                    else:
                        ranked_win_rate[1] += 1
           
                # If not ranked, it's either a custom game or unranked matchmaking game
                if is_custom:
                
                    player_stats_customs += kda
                    custom_games += 1
                    # Without a team color assigned, must be FFA
                    if not team_color_buffer:
                        custom_ffa_games += 1
                    else:
                        custom_team_games += 1
                        dictionary_insert(team_color_buffer, team_color_customs_dictionary)


                    
            # Process team colors in team customs
            if i[0] in team_list:
                # Update Team color as rows get parsed
                team_color_buffer = i[0]
                # Win Rate - 
                # @NOTE - programming is getting sloppy...too many late nights.  
                if not winning_tracker[0]:
                    winning_tracker[0] = True
                else :
                    winning_tracker[1] = True

    # Sort the player dictionary by most played with --> least
    sorted_player_list = sorted(player_dictionary.items(), key = lambda x:x[1], reverse=True)
    # Sort the map dictionary by most played --> least
    sorted_map_played_list = sorted(map_dictionary.items(), key=itemgetter(1), reverse=True)
    # Sort the game_type dictionary by most played --> least
    game_type_list_sorted  = sorted(game_type_dictionary.items(), key=itemgetter(1), reverse=True)
    # Sort the playlist dictionary by most played --> least
    playlist_list_sorted   = sorted(playlist_dictionary.items(), key=itemgetter(1),reverse=True)
    # Sort the Clans played in by most played with --> least
    clans_list_sorted      = sorted(clans_dictionary.items(), key=itemgetter(1), reverse=True)
    # Sort the Team Color chosen in team custom games by most selected --> least
    team_color_customs_list_sorted = sorted(team_color_customs_dictionary.items(), key=itemgetter(1), reverse=True)
    # Sort the Team Color chosen in team ranked games by most selected --> least
    team_color_ranked_list_sorted = sorted(team_color_ranked_dictionary.items(), key=itemgetter(1), reverse=True)
    # Sort the games played per day dictionary
    games_played_per_day_list_sorted = sorted(date_dictionary.items(), key=itemgetter(1), reverse=True)

    #output_file.write(s + '\n')
    
    def write_stat(s):
        output_file.write(s + '\n') 
        
    
    ''' Beginning of the Outputs '''
    global purged_games
    s = "\nTotal Games Purged: " + str(purged_games).rjust(4) + "\n"
    write_stat(s)
    
    # Outputs the sorted list of Maps by most played
    s = "\nMap Selection Frequency\n--------------------------------------"
    write_stat(s) 
    
    for i in sorted_map_played_list:
        # Create a nicely formatted string showing "map : count / total_games"
        s = i[0].ljust(15) + ": " + str(i[1]).rjust(5) + " / " + total_games + " | " + "{:.2%}".format(int(i[1])/int(total_games)).rjust(6)
        write_stat(s) 
     
    # Outputs the sorted list of Game Types by most played
    s = "\nGame Type Frequency\n-------------------------------------------"
    write_stat(s) 
     
    for i in game_type_list_sorted:
        # Create a nicely formatted string showing "game_type : count / total_games"
        s = i[0].ljust(20) + ": " + str(i[1]).rjust(5) + " / " + total_games + " | " + "{:.2%}".format(int(i[1])/int(total_games)).rjust(6)
        write_stat(s) 
        
    # Outputs the sorted list of Playlist by most played
    s = "\nPlaylist Frequency\n-------------------------------------------"
    write_stat(s)  
        
    for i in playlist_list_sorted:
        # Create a nicely formatted string showing "game_type : count / total_games"
        s = i[0].ljust(20) + ": " + str(i[1]).rjust(5) + " / " + total_games + " | " + "{:.2%}".format(int(i[1])/int(total_games)).rjust(6)
        write_stat(s) 

    # Outputs the sorted list of Clans by most played with
    s = "\nClanmatch Frequency\n--------------------------------------------"
    write_stat(s) 
        
    for i in clans_list_sorted:
        # Create a nicely formatted string showing "game_type : count / total_games"
        s = i[0].ljust(20) + ": " + str(i[1]).rjust(5) + " / " + str(clanmatch_games) + " | " + "{:.2%}".format(int(i[1])/int(clanmatch_games)).rjust(7)
        write_stat(s)  
            
    # Outputs the sorted list of Team Color by most played as in Customs
    if custom_team_games != 0:
        s = ""
        s += "\nTeam Color [Customs] Selection Frequency\n----------------------------------------\n"   
        for i in team_color_customs_list_sorted:
            # Create a nicely formatted string showing "game_type : count / total_games"
            s += i[0].ljust(20) + ": " + str(i[1]).rjust(5) + " / " + str(custom_team_games) + " custom team games | " + "{:.2%}".format(i[1]/custom_team_games).rjust(7) + "\n"
        write_stat(s)           
       
    # Outputs the sorted list of Team Color by most played as in Ranked
    s = "\nTeam Color [Ranked] Selection Frequency\n---------------------------------------\n"
    for i in team_color_ranked_list_sorted:
        if i[1]:
            # Create a nicely formatted string showing "game_type : count / total_games"
            s += i[0].ljust(20) + ": " + str(i[1]).rjust(5) + " / " + str(ranked_team_games) + " ranked team games | " + "{:.2%}".format(i[1]/ranked_team_games).rjust(7) + "\n"
    write_stat(s) 
            
            
    # Parses the date dictionary for highest value and outputs the day and count for most games played 
    s = ""
    s += "\n"
    s += "Top 15 days with most games played:\n-----------------------------------\n"
    for i in range(0, 15):
        try:
            s += "  " + games_played_per_day_list_sorted[i][0].rjust(10) + ": " + str(games_played_per_day_list_sorted[i][1]).rjust(4) + "\n"
        except:
            pass
    write_stat(s)

    # Parses the time dictionary for highest value and outputs the time and count for most games played
    s = ""
    s += "\n"
    s += "Most games played at this hour:\n-------------------------------\n"
    most_hour_played = key_with_max_value(time_dictionary)
    s += most_hour_played + " : " + str(time_dictionary[most_hour_played]) + " games played at this hour"
    write_stat(s)

    # Outputs a complete hour by hour breakdown of games played
    s = ""
    s += "\n"
    s += "Complete hour by hour breakdown (CST):\n--------------------------\n"
    s += dict_to_string(time_dictionary)
    write_stat(s)

    # Outputs a complete day by day breakdown of games played
    s = ""
    s += '\n'
    s += "Complete day by day breakdown:\n------------------------------\n"
    s += dict_to_string(weekday_dictionary)
    write_stat(s)

    '''
    # @TODO - Remove? Already in list above...
    # Parses the playlist dictionary for highest value and outputs the playlist and count for most games played
    s = ""
    s += "\n"
    s += "Most frequently played playlist:\n--------------------------------\n"
    most_played_playlist = key_with_max_value(playlist_dictionary)
    s += most_played_playlist + " : " + str(playlist_dictionary[most_played_playlist]) + " games played in this playlist."
    write_stat(s)
    '''

    # Build stat table for Ranked vs. Unranked.  Uses hardcoded justify and % format 
    s = ""
    s += "\nRanked vs. Unranked:\n------------------------------------------"
    s += "\nRanked Games: ".ljust(18) + str(ranked_games).rjust(6) + " / " + str(total_games).rjust(5) + " | " + "{:.2%}".format(int(ranked_games)/int(total_games)).rjust(7)
    s += "\n                   ----------------------"
    s += "\nUnranked Games: ".ljust(18) + str(unranked_games).rjust(6) + " / " + str(total_games).rjust(5) + " | " + "{:.2%}".format(unranked_games/int(total_games)).rjust(7)
    s += "\n                   ----------------------"
    s += "\nCustom Games: ".ljust(18) + str(custom_games).rjust(6) + " / " + str(total_games).rjust(5) + " | " + "{:.2%}".format(custom_games/int(total_games)).rjust(7)
    s += "\n                   ----------------------"
    if custom_games:
        s += "\n  [Team]: ".ljust(18) + str(custom_team_games).rjust(6) + " / " + str(custom_games).rjust(5) + " | " + "{:.2%}".format(custom_team_games/int(custom_games)).rjust(7)
        s += "\n  [FFA ]: ".ljust(18) + str(custom_ffa_games).rjust(6) + " / " + str(custom_games).rjust(5) + " | " + "{:.2%}".format(custom_ffa_games/int(custom_games)).rjust(7)
    s += "\n------------------------------------------"
    s += "\nClan Matches: ".ljust(18) + str(clanmatch_games).rjust(6) + " / " + str(total_games).rjust(5) + " | " + "{:.2%}".format(clanmatch_games/int(total_games)).rjust(7)
    s += "\n                   ----------------------"
    if clanmatch_games:
        s += "\n  [Minor]: ".ljust(18) + str(clanmatch_games_minor).rjust(6) + " / " + str(clanmatch_games).rjust(5) + " | " + "{:.2%}".format(clanmatch_games_minor/int(clanmatch_games)).rjust(7)
        s += "\n  [Major]: ".ljust(18) + str(clanmatch_games_major).rjust(6) + " / " + str(clanmatch_games).rjust(5) + " | " + "{:.2%}".format(clanmatch_games_major/int(clanmatch_games)).rjust(7)
    write_stat(s)

    s = ""
    s += "\n"
    s += "\n           Maximum Rank Achieved overall: " + str(max_rank_overall[0]).rjust(3) + " in game ID " + str(max_rank_overall[1])
    s += "\nMaximum Rank Excl. Clan Achieved overall: " + str(max_rank_no_clan[0]).rjust(3) + " in game ID " + str(max_rank_no_clan[1])
    write_stat(s)


    # Outputs a complete hour by hour breakdown of games played
    s = ""
    s += "\n"
    s += "Complete Monthly Ranked K/D breakdown:\n--------------------------------\n"
    for month, kda in monthly_kda_dictionary.items():
        try:
            s += month.ljust(10) + ": " + "{:.3f}".format(kda[0]/kda[2]).rjust(5) + " over " + str(int(kda[3])).rjust(4) + " games\n"
        except:
            s += month.ljust(10) + ": 0.00 over 0 games\n"
    write_stat(s)


    # Output total K/D/A's & ratios 
    s = ""
    s += "\n"
    s += "\nKills / Assists / Deaths Overview:                                                                     K/D "
    s += "\n-----------------------------------------------------------------------------------------------------------"
    s += "\nGlobal Kills / Assists / Deaths:".ljust(55) 
    s += str(player_stats_global[0]).rjust(6) + " Kills | " + str(player_stats_global[1]).rjust(6) + " Assists | " + str(player_stats_global[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_global[0]/player_stats_global[2]).rjust(5)
    s += "\nRanked Kills / Assists / Deaths:".ljust(55) 
    s += str(player_stats_ranked[0]).rjust(6) + " Kills | " + str(player_stats_ranked[1]).rjust(6) + " Assists | " + str(player_stats_ranked[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_ranked[0]/player_stats_ranked[2]).rjust(5)
    s += "\nRanked Team Kills / Assists / Deaths:".ljust(55) 
    s += str(player_stats_ranked_team[0]).rjust(6) + " Kills | " + str(player_stats_ranked_team[1]).rjust(6) + " Assists | " + str(player_stats_ranked_team[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_ranked_team[0]/player_stats_ranked_team[2]).rjust(5)
    s += "\nRanked FFA Kills / Assists / Deaths:".ljust(55) 
    s += str(player_stats_ranked_ffa[0]).rjust(6) + " Kills | " + str(player_stats_ranked_ffa[1]).rjust(6) + " Assists | " + str(player_stats_ranked_ffa[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_ranked_ffa[0]/player_stats_ranked_ffa[2]).rjust(5)
    s += "\nRanked Excl. Clanmatches Kills / Assists / Deaths:".ljust(55) 
    s += str(player_stats_ranked_no_clan[0]).rjust(6) + " Kills | " + str(player_stats_ranked_no_clan[1]).rjust(6) + " Assists | " + str(player_stats_ranked_no_clan[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_ranked_no_clan[0]/player_stats_ranked_no_clan[2]).rjust(5)
    s += "\nClanmatch Kills / Assists / Deaths:".ljust(55) 
    s += str(player_stats_clan[0]).rjust(6) + " Kills | " + str(player_stats_clan[1]).rjust(6) + " Assists | " + str(player_stats_clan[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_clan[0]/player_stats_clan[2]).rjust(5)
    s += "\nCustoms Kills / Assists / Deaths:".ljust(55) 
    s += str(player_stats_customs[0]).rjust(6) + " Kills | " + str(player_stats_customs[1]).rjust(6) + " Assists | " + str(player_stats_customs[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_customs[0]/player_stats_customs[2]).rjust(5)
    s += "\nMatchmaking Kills / Assists / Deaths:".ljust(55) 
    s += str(player_stats_matchmaking[0]).rjust(6) + " Kills | " + str(player_stats_matchmaking[1]).rjust(6) + " Assists | " + str(player_stats_matchmaking[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_matchmaking[0]/player_stats_matchmaking[2]).rjust(5)
    write_stat(s)

    # Map specific K/D
    s = ""
    s += "\n"
    s += "\nMap Specific K/D: "
    s += "\n----------------------\n"
    # Alphabetically sort the maps
    map_kd_dictionary = dict( sorted(map_kd_dictionary.items(), key=lambda x: x[0].lower()) )
    # Calculate the k/d from the first 3 elements and store in 4th
    for m, kda in map_kd_dictionary.items():
        kda[3] = kda[0]/kda[2]
        s += m .ljust(15) + ": " + "{:.3f}".format(kda[3]) + "\n"
    write_stat(s)

    # Most Players played w/ preview
    s = ""
    s += "\n"
    s += "\nTop 100 Most Played with:\n------------------------\n"
    for i in range(0, 100):
        try:
            s += "  " + sorted_player_list[i][0].ljust(16) + ": " + str(sorted_player_list[i][1]).rjust(5) + "\n"
        except:
            pass
    write_stat(s)

    # Win Rate Outputs
    s = ""
    s += "\n"
    s += "\nRanked Team Excl. Clan Win Rate\n--------------------------------"
    wins = int(ranked_win_rate[0])
    losses = int(ranked_win_rate[1])
    if ranked_team_games != 0:
        rate = float(wins/(ranked_team_games))
        s += "\nWins: " + str(wins).rjust(5) + " | Losses : " + str(losses).rjust(5) + " | Win Rate: " + "{:.2%}".format(rate).rjust(5) 
    write_stat(s)


    # Head to Head Mode:
    if vs_gamertag:
        s = ""
        s += "\n"
        s += "\nHead to Head - Ranked Games Only"
        s += "\n--------------------------------"
        s += "\nGamertag(s): " + str(gamertag).ljust(80, '-') + " | " + "{:.3f}".format(head_to_head_player[0]/head_to_head_player[2]).rjust(5)
        s += "\n  vs."
        s += "\nGamertag(s): " + str(vs_gamertag).ljust(80, '-') + " | " + "{:.3f}".format(head_to_head_opponent[0]/head_to_head_opponent[2]).rjust(5)
        s += "\n"
        s += "\nData taken from " + str(head_to_head_games) + " games."
        write_stat(s)
    
    updateGlobalStatus("Done parsing.")
    output_file.close()
    
def updateGameCount(gt):
    print("GGGG")
    
def totalGameCount(gamertag):
    URL = 'https://halo.bungie.net/stats/PlayerStatsHalo2.aspx?player='+gamertag
    soup = []
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')
    # don't ask - just took the closest field to the total games
    try:
        total_games = soup.find("div", {"class": "rgWrap rgInfoPart"}).get_text("|", strip=True).split('|')[0]
    except:
        total_games = "N/A"
    
    return total_games
    
class App(Frame):
    def __init__(self,master=None):
        Frame.__init__(self, master)
        self.master = master
        
        self.root_label = Label(text="Working Directory:")
        self.root_label.grid(row=0, column=0,stick=W)
        
        self.root_entry = Entry(width=69)
        self.root_entry.delete(0,END)
        self.root_entry.insert(0, root_directory)
        self.root_entry.grid(row=0, column=1, columnspan=3,sticky=W)
        
        self.directory_button = Button(text="...", command=lambda: browseDirectory(self.root_entry ))
        self.directory_button.grid(row=0, column=5)
        
        self.Gamertags_label = Label(text="Gamertag(s):")
        self.Gamertags_label.grid(row=1,column=0,sticky=W)
        
        self.head2head_label = Label(text="Compare stats w/:")
        self.head2head_label.grid(row=1,column=1,sticky=W)
        
        self.gamertag_entry = []
        self.head2headgt_entry = []

        for i in range(5):
           
           self.gamertag_entry.append(Entry(width=16))
           self.gamertag_entry[i].grid(row=i+2,column=0)
           self.gamertag_entry[i].bind("<<Leave>>", lambda event:updateGameCount(self.gamertag_entry[i]))
           
           self.head2headgt_entry.append(Entry(width=16))
           self.head2headgt_entry[i].grid(row=i+2,column=1,sticky=W)
            
        self.current_game = StringVar()
        self.game_selection = {'Halo 2','Halo 3 (Coming Soon?)'}
        self.current_game.set('Halo 2')
        self.game_select_menu = OptionMenu(master, self.current_game, *sorted(self.game_selection))
        self.game_select_menu.grid(row=1,rowspan=2,column=2,columnspan=3,sticky=EW)
        
        self.generate_text = StringVar()
        self.generate_text.set("Download Halo Stats")
        self.download_stats = Button(textvariable=self.generate_text, font = ('Sans','10','bold'), command=lambda: threadButtonDownload(self.gamertag_entry))
        self.download_stats.grid(row=3,rowspan=2,column=2,columnspan=3,sticky=EW)
        self.download_stats.grid_columnconfigure(0, weight=1)
        
        #Unused - not enough time for web page saves
        # Original goal was to say "already downloading the web page for the carnage report, might as well SAVE the webpage entirely"
        '''
        self.save_offline = IntVar()
        self.save_offline.set(1)
        self.save_offline_checkbox = Checkbutton(text="Save Offline Copy", variable=self.save_offline)
        self.save_offline_checkbox.grid(row=5,columnspan=3,column=2,sticky=EW)
        '''
        
        self.parse_stats = Button(text="Parse Halo Stats", font = ('Sans','10','bold'), command=lambda: threadButtonParse(self.gamertag_entry))
        self.parse_stats.grid(row=6,rowspan=2,column=2,columnspan=3,sticky=EW)
        self.parse_stats.grid_columnconfigure(0, weight=1)
        
        self.status_label = Label(text="", fg="Red", font='Helvetica 12 bold')
        self.status_label.grid(row=8,column=0,columnspan=6,sticky=W)
        
        self.readme_label = Text(master)
        global readme_string
        self.readme_label.insert(END, readme_string)
        self.readme_label.grid(row=9,column=0,columnspan=6,sticky=EW)
        self.readme_label.config(state=DISABLED)
        
        self.updateStatus()
    
    def updateStatus(self):
        # Use global status variable so it can lazily be modified from anywhere
        global status
        # Update status label at bottom
        self.status_label.configure(text=status)

        self.after(1000, self.updateStatus)

# Tkinter Initialization
root = Tk()
app = App(root)
root.wm_title("Halo Stat Saver / Parser")
root.mainloop()
Tk.quit(root)
