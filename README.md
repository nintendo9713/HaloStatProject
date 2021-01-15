# Halo2StatProject
Python code for saving Halo 2 stats from gamertags from Bungie.net

I am currently moving over the next 2 months, but plan to clean up all of this as a nail in the coffin.  Just give me some time.

*Preamble - my hope is by the time I write out this absurdly detailed question, I'll have thought of an implementation.  I'm a C/C++ programmer by trade, but pretty new to Python. This type of exercise may help solve my own problem.   I know ahead of time this will be long, and I don't expect many people to read this far after seeing the length.*

I am parsing 200,000+ games of Halo 2 saved in a single file.  Each line represents a game with all available information (numerous parameters have been purged since 2004).  I have handled everything but the "carnage report", which is the Player/Kills/Death board.  This is because they aren't uniform.  

A carnage report **always** consists of a 8-item wide **Header** row:

    ['Players', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score']

The next 8 fields depend if it's a Team-Game, or Free-For-All.  If it's a Free-for-All, the next 8 fields will represent a player - like this:

    'Agnt 007', '8', '1', '2', '+6', '0', '0', '8'

This also means every 8-items is a different player with their fields, and is easy to reorder the list as a 2D array like:

    # Grab the carnage report and drop the "]["
    #     (for the sake of this example, assume results is a list, not a string)
    results = structure.split('|')strip('][')[2]
    size = len(results)
    print(np.array(results).reshape(int(size/8),8))

Now results[0] is the **Header**, and the following rows are the players in the game where I can extract cumulative kills/deaths.

However, if it's a Team-Game, following the **Header** , It will have an 8-wide section for each team's totals (sorted by highest score), a **TeamHeader** if you will, as such:

    'Red Team', '50', '16', '43', '+7', '0', '0', '50'

Other teams **may** also be present throughout (odd scenarios where everyone played a game on one team with no opponents), and any player following that Team-Row was on that team.  Now - I can make a **"TeamList"** of ['Red Team','Blue Team','Green Team' ... ].  I can check if *player*, which in this case is *'Red Team'*, is in **TeamList**, then I know it's not a player's row, and can either ignore - or add to a dictionary about team color frequency.  Simple stuff - *(unless someone's Xbox Live gamertag was 'Red Team' or another color, then it would break this)*

But here's the curve ball - if a game is **ranked**, the **Header** is the same 8-wide list, the **TeamHeader**'s are 8 wide, but now each player has 9 fields.  Players now have:

    ['Players', 'Rank', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score']

Easy fix right? If game is ranked:

    results.insert('Rank', 1)
    for i in results:
        # if entry is 'Red Team', 'Blue Team', etc.
        if i in TeamList:
          results.insert('-', results.index(i))

Now the player fields are 9 wide, the headers are 9 wide, and I can change that above algorithm to be:

    .reshape(int(size/9)/9)

Now that I've got that under control - we can apply that logic to the following two scenarios:  Ranked Free-for-All, and Unranked Free-for-All:

    if is_ranked == True:
        results.insert('Rank', 1)
        results.reshape(int(size/9)/9)
    else:
        results.reshape(int(size/8)/8)
    for i in results:
        if i[0] not in TeamList:
           # is player - process all 9 items in his row
            process_carnage(i)
     
Now, *process_carnage(p)* can check len(p) to see if it's 8 or 9 and process accordingly.  Then I thought - what if I just always inject 'Rank' at [1], and even if it's not ranked - put 'n/a', '-1', or  '0' as the rank for each player in that unranked game*(0 did not exist as a rank)*.  

The final curve ball - **Clan Matches**.  These are ranked, and there is a flag that verifies the game was a clan match, but instead of saying *'Red Team'* and *'Blue Team'*, it's the clan named by a 12 year old.  These are indiscernible from an Xbox Live gamertags since they have the same requirements.  Immediately following the **Header** is the the clan that won (or if tied, a toss-up).  So if we injected 'Rank' at [1] of the list, the second set of 9, or `results[1]` after reshaping, we will have a clan name instead of 'Red/Blue Team', 

.

.

.

If a Gametype is a team game, there will be an entry for "<Red/Blue/Green Team>, Team Kills, Team Assists, Team Deaths, etc...>.  There are no additional entries in Free-for-All gametypes.

If a Playlist is ranked, there will be an **extra** field (the current XP level) between the player and kills, thus making the rows 9 wide instead of 8.  The "header" is still 8 wide.  If a playlist is unranked, the "header" is 8 fields wide ['Players', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score']. it's as simple as this:

    # Grab the carnage report and drop the "]["
    #     (for the sake of this example, assume results is a list, not a string)
    results = structure.split('|')strip('][')[2]
    size = len(results)
    print(np.array(results).reshape(int(size/8),8))

If a playlist is ranked, which I have the flag to show if it was, I insert "rank" as such:
    # Grab the carnage report and drop the "]["
    #     (for the sake of this example, assume results is a list, not a string)
    results = structure.split('|')strip('][')[2]
    size = len(results)
    print(np.array(results).reshape(int(size/8),8))
There are 7 types of carnage reports:

    # Team game - Matchmaking - Unranked
    [77437379]|['Team Slayer on Colossus', 'Playlist - Team Training', '2/7/2005, 12:31 PM PST', 'Unranked']|['Players', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score', 'Blue Team', '43', '22', '42', '+1', '0', '0', '43', 'Soup Natsi', '14', '4', '12', '+2', '0', '0', '14', 'ForgotenWarrior', '13', '5', '8', '+5', '0', '0', '13', 'OOALEX', '9', '10', '9', '0', '0', '0', '9', 'KnirpsElf', '7', '3', '13', '-6', '0', '0', '7', 'Red Team', '42', '16', '43', '-1', '0', '0', '42', 'madfighter117', '17', '4', '12', '+5', '0', '0', '17', 'Sk8Stud1024', '14', '5', '13', '+1', '0', '0', '14', 'DirtyCajun', '9', '3', '14', '-5', '0', '0', '9', 'SpyingGoat', '2', '4', '4', '-2', '0', '0', '2']
    # Team Game - Matchmaking - Ranked
    [336100763]|['Neutral Flag on Sanctuary', 'Playlist - Team Skirmish', '10/29/2005, 8:51 AM PDT', 'Ranked']|['Players', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score', 'Blue Team', '34', '12', '17', '+17', '0', '0', '5', 'llm3zm0riz3jrll', '18', '5', '2', '4', '+1', '0', '0', '3', 'Glockologist', '21', '9', '2', '6', '+3', '0', '0', '1', 'pRoXii', '12', '17', '1', '3', '+14', '0', '0', '1', 'the gixxer', '18', '3', '7', '4', '-1', '0', '0', '0', 'Red Team', '17', '7', '34', '-17', '0', '0', '3', 'sneak BR', '17', '4', '1', '11', '-7', '0', '0', '2', 'pikeyboy', '18', '6', '0', '6', '0', '0', '0', '1', 'Orog', '18', '2', '3', '8', '-6', '0', '0', '0', 'STRONG WAVE', '18', '5', '3', '9', '-4', '0', '0', '0']
    # Team Game - Matchmaking - Clanmatch - Ranked
    [75466857]|['Team Slayer on Foundation', 'Playlist - Minor Clanmatch', '2/5/2005, 11:38 AM PST', 'Ranked']|['Players', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score', 'S0NS OF LIBERTY', '50', '20', '38', '+12', '0', '0', '50', 'CactusJack00', '14', '15', '4', '9', '+6', '0', '0', '15', 'Major Jigaboo', '14', '14', '6', '10', '+4', '0', '0', '14', 'LnP Obliterator', '14', '11', '7', '11', '0', '0', '0', '11', 'Agnt 007', '14', '10', '3', '8', '+2', '0', '0', '10', 'The Testament', '38', '18', '50', '-12', '0', '0', '38', 'Wilkz', '12', '16', '4', '10', '+6', '0', '0', '16', 'martin1444', '12', '10', '4', '11', '-1', '0', '0', '10', 'Fatesman X', '12', '6', '6', '13', '-7', '0', '0', '6', 'SpykX', '12', '6', '4', '16', '-10', '0', '0', '6']
    
    # Custom game - Free for all - Unranked
    [188652100]|['Slayer on Headlong', 'Playlist - Arranged Game', '5/29/2005, 9:45 PM PDT', 'Unranked']|['Players', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score', 'EvansAlvarez', '2', '1', '1', '+1', '0', '0', '2', 'Kojangie', '1', '0', '7', '-6', '0', '0', '1', 'Agnt 007', '1', '0', '1', '0', '0', '0', '1']
    # Custom game - Team Game - Unranked
    [61882257]|['Slayer on Foundation', 'Playlist - Arranged Game', '1/21/2005, 11:07 PM PST', 'Unranked']|['Players', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score', 'Green Team', '0', '0', '0', '0', '0', '0', '0', 'P0PP', '0', '0', '0', '0', '0', '0', '0', 'Red Team', '0', '0', '0', '0', '0', '0', '0', 'ba1ingb1ing', '0', '0', '0', '0', '0', '0', '0', 'B1oodshed', '0', '0', '0', '0', '0', '0', '0', 'SilverSpoon102', '0', '0', '0', '0', '0', '0', '0', 'Standby 4 Nerds', '0', '0', '0', '0', '0', '0', '0', 'Leviathan II', '0', '0', '0', '0', '0', '0', '0', 'BlueWolf113', '0', '0', '0', '0', '0', '0', '0', 'Agnt 007', '0', '0', '0', '0', '0', '0', '0', 'ak general', '0', '0', '0', '0', '0', '0', '0']
    
    # Free for all - Matchmaking - Unranked
    [62486903]|['Rumble Slayer on Ascension', 'Playlist - Rumble Pit', '1/22/2005, 2:28 PM PST', 'Ranked']|['Players', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score', 'Agnt 007', '11', '26', '6', '3', '+23', '0', '0', '25', 'Lethal Sword', '10', '11', '0', '9', '+2', '0', '0', '11', 'Mr NovembeRRR', '10', '8', '6', '9', '-1', '0', '0', '8', 'cadillac04', '9', '7', '2', '11', '-4', '0', '0', '7', 'Johnny000000', '10', '6', '4', '11', '-5', '0', '0', '6', 'JumboShrimp', '9', '5', '2', '9', '-4', '0', '0', '5', 'Psic Killa', '8', '5', '3', '12', '-7', '0', '0', '4', 'StLWarrior', '8', '2', '2', '8', '-6', '0', '0', '2']
    # Free for all - Matchmaking - Unranked
    [63130390]|['Rumble Slayer on Lockout', 'Playlist - Rumble Training', '1/22/2005, 10:50 PM PST', 'Unranked']|['Players', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score', 'Agnt 007', '25', '4', '2', '+23', '0', '0', '25', 'parra 1(G)', '11', '3', '10', '+1', '0', '0', '11', 'FUB 420', '9', '1', '6', '+3', '0', '0', '9', 'RapindomeS', '8', '4', '10', '-2', '0', '0', '8', 'parra 1(G)', '7', '2', '11', '-4', '0', '0', '7', 'parra 1', '4', '3', '13', '-9', '0', '0', '4', 'FUB 420(G)', '3', '1', '15', '-12', '0', '0', '3']
    
