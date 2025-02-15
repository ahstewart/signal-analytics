A little script that leverages Dash/Plotly and Signal's SQLite DB to display a "Spotify Wrapped"-style dashboard of Signal conversation analytics.

# Requirements
If you want to use this to try to generate analytics for your own Signal data, you'll at the very least need the following:
* Signal desktop (and have used it for a long-enough time period to have amassed a useful amount of data)
* Linux distro (makes database decryption much easier)
* Courage (this is a hacky weekend project that was never meant to be made available to others, it's a mess)

# Set Up
Start by cloning this repo.

## Config File
Next, you'll need to create a config file. The script expects the config file to be TOML-format, titled "config.toml", and located in the same directory. If I end up spending more time on this, I'll make the config file name and path configurable run-time parameters for ease of use.

The requried config parameters are:
* year = 2024 # year to be used in title
* start_date = '2024-01-01 00:00:00' 
* end_date = '2024-12-31 00:00:00'
* emojis_shown = 15 
* db_path =  # path to the decrypted db.sqlite database
* conv_id = # UUID of Signal conversation to be used (conversation = "group chat")

## Database
The last step, but no doubt the one with the most potential to be frustrating, is getting your Signal data into a database that the script can access. If you use Signal desktop, all of your app data is stored in an ecnrypted SQLite database somewhere in your file system. The exact location depends on your OS.

What you'll need to do is find this database, make a copy of it, and decrypt the copy. The decryption process is heavily documented in other areas online, but just a word of advice - I had an exponentially easier time with decryption in a Linux OS, rather than Windows.

### Find a Conversation ID
Once you've decrypted the database, you can find the final config value - the conv_id. To do this, you'll need to use any old sqlite viewer tool to peek into the DB, specifically the conversations table, and find one of interest.

# Running the Dashboard
Once you're all set up with the above, you should be able to simply run the `analytics.py` script, navigate to your local host, port 8000 in your web browser, and see the analytics.

A word of caution: The main reason we use Signal is to keep our data secure and private. End-to-end encryption is only as effective as its ends. This act of decrypting your Signal data, building analytics on top of it, and then potentially sharing these analytics with others can pose data security issues if proper precautions aren't put into place. 
