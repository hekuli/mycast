Your job is to collect custom news information from the internet and save it into a text file. Then use this text file to generate an mp3 podcast using TTS. Then publish the new podcast episode by uploading it to a CloudFlare R2 bucket.  

Run the Setup steps, then run the Execution steps below, then finally the Status Report.

Success criteria is that the following are uploaded to the R2 `mycast` bucket:
- A new non-empty txt file with today's podcast transcript.
- A new mp3 audio file of today's podcast, should be greater than 5 mins in length.
- An updated `feed.xml` that includes references to the new transcript and mp3 files.

If there are any errors along the way keep trying until you succeed. If you cannot achieve all success criteria in under 1 hour, report back the reasons why via a Status Report. Otherwise report the success info to the Status Report.

Note: in the instructions the string `YYYY-MM-DD` is frequently used. This should always be replaced with a valid date related to the task.


## Setup

1. Clone the repo (if you haven't already)
2. Install any missing script dependencies. All details are in the repo inside `README.md` and `SETUP.md`.
3. Install `ffmpeg` (this is needed to convert the wav file to mp3).
4. Install `rclone` (this is needed to download/upload the podcast files).
The rclone config should look like this:
```
[r2]
type = s3
provider = Cloudflare
access_key_id = <R2_ACCESS_KEY_ID>
secret_access_key = <R2_SECRET_ACCESS_KEY>
endpoint = <R2_ENDPOINT>
```
5. Configure `rclone` to add a new CloudFlare backend withe the provided secrets, and name it `r2`.


## Execution

1. From the R2 bucket called `mycast`, download the main `feed.xml` file and last 10 text transcript files (they are named by date in format: YYYY-MM-DD.txt). Put them all into `./output/`. 
```
rclone copy r2:mycast/feed.xml ./output
rclone copy r2:mycast/YYYY-MM-DD.txt ./output       # replace with yesterday's date
rclone copy r2:mycast/YYYY-MM-DD.txt ./output       # replace with the day before yesterday's date
# etc for all 10 days
```
2. Execute the Data Collection task and create the text file transcript (more on this below under heading "Data Collection"), save the resulting transcript to: `./incoming/YYYY-MM-DD.txt`
3. Run the repo script command to generate the mp3 from the transcript:
```
uv run python main.py tts ./incoming/YYYY-MM-DD.txt -f ./output/feed.xml
```
4. Sync the the results back to the R2 bucket
```
rclone copy ./output/YYYY-MM-DD.txt r2:mycast
rclone copy ./output/YYYY-MM-DD.mp3 r2:mycast
rclone copy ./output/feed.xml r2:mycast
```

### Data Collection

This is the bulk of your execution work. Your job here is to search the internet and create a summary report of the news stories I care about from the topics and sources I prefer. Stories should be chosen based on how meaningful or popular they are. Each source can have specific instructions to also adhere to in the `mycast-user-settings.md` file. Omit any globally or source-specific blacklisted topics. If a category is configured in the settings, present all stories from that source in that category. Stories should be grouped by these categories.

## Criteria for Web Research
- Do not include any summary info at the top or bottom, it's unnecessary.
- Each topic should include a descriptive title, and a basic summary (no more than 5 lines). The summary should not duplicate the title contents.
- All results should be in English.
- Do not repeat stories from previous reports.
- Do not provide extensive background information on stories, just report what's new.
- Always include human readable source(s) for each story, i.e. "Source: Hacker News" or "Reddit /r/Swift"
- Don't go out of your way to add stories to a category just to have coverage for a category. It's totally fine to have no stories for a category if nothing is particularly new or newsworthy.
- Target having about 20-30 minutes of spoken content. That means the total number of words in the output file should not exceed: 6,000.
- Avoid repeating topics/stories even if they exist in multiple sources. 

IMPORTANT: The `mycast-user-settings.md` file for personalization is available in this GitHub Gist: `https://gist.github.com/hekuli/1aa585cba3a5ebf29e1e71d8ff27498c`. This contains the bulk of the customized instructions. Download it, read it, and understand it. 

IMPORTANT: Before conducting the research, read the last 10 transcripts (or however many are available) under `./output` so you don't duplicate or repeat things from previous days.

Then execute the research.

Output the data as a readable plain text transcript text file to: `./incoming/YYYY-MM-DD.txt`. This output file should be formatted such that it can be easily be read by TTS models (like Kitten TTS) to turn into an audio file (research that here: https://github.com/KittenML/KittenTTS). 


## Status Report

Send a status report to a Telegram chat using curl and the following. Replace variables with the environment variables provided in the routine.

curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/sendMessage" \
  -d "chat_id=<TELEGRAM_CHAT_ID>" \
  -d "text=status update message goes here"


