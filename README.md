<h1 align="center">Slack Paint</h1>

<p align="center">
  <img src="https://github.com/user-attachments/assets/03d4492c-2b95-4c2a-a89f-ca5ebd0976ad" alt="Slack Paint Screenshot" width="600"/>
</p>


<details open>
<summary><strong>Table of Contents</strong></summary>

- [FAQ](#how-do-i-send-my-beautiful-creation-to-other-people)
  - [How do I send my beautiful creation to other people?](#how-do-i-send-my-beautiful-creation-to-other-people)
  - [When I paste my message not all emojis load in!](#when-i-paste-my-message-not-all-emojis-load-in)
  - [My message is too big to be sent over Slack/Discord!](#my-message-is-too-big-to-be-sent-over-slackdiscord)
  - [Why does converting an image take so long the first time?](why-does-converting-an-image-take-so-long-the-first-time)
- [How to run?](#how-to-run)
  - [Option 1 - install the .exe](#option-1---install-the-exe---quickest-and-easiest)
  - [Option 2 - Run the Python program yourself](#option-2---run-the-python-program-yourself)
- [How to use this tool](#how-to-use-this-tool)
  - [Drawing patterns](#drawing-patterns)
- [How to import Slack emojis](#how-to-import-slack-emojis)
- [How can I make these mosaics/pixel art out of emojis?](#how-can-i-make-these-mosaicspixel-art-out-of-emojis)
- [How to import Discord emojis](how-to-import-discord-emojis)

</details>

---
<details open>
<summary><h2>FAQ</h2></summary>

### How do I send my beautiful creation to other people?
You can copy whatever you just drew/created by pressing the "Copy" button at the bottom, then you can simply paste your creation as a message.

### When I paste my message not all emojis load in!
This is a comment issue when sending a lot of different emojis in one message, you can make all emojis load by either re-pasting the message, or switching to another chat and coming back.

### My message is too big to be sent over Slack/Discord!
Both Slack and Discord, (and probably any other chat system) have a limit to how many characters you can send in one message.<br>
Since emojis in these applications are made of :emoji_name: **a single emoji does not equal one character!** And thus, you might reach this limit a lot sooner than you think. There isn't really any way to get around this (**but there is a small trick for Salck I will mention at the end of this paragraph**), there are a few ways to shorten your message:
- One thing you can do is scale down your message. If this is a recreation of an image, you can use the width and height settings to scale the recreation. If you are using Discord, unless you have Discord Nitro, most likely image creation won't be a viable feature due to the small message limit.
- You can also shave off part of your message, maybe you have some empty space at the end of your message, you can simply cut off
- use different emojis, maybe you have some shorter named emojis you can use instead, all emoji's even if already placed, can be changed by adjusting their associated text box or clicking on the emoji next to the text box and swapping it.<be>

<strong>As for the trick to get around part of Slack's message limit:</strong><br>
You can partially get around slacks message limit by sending any message to a person and then editing this message, which will seemingly double the amount of characters you can send in one message.

### Why does converting an image take so long the first time?
As we don't actually save/download any picture locally, we instead make some web request to get the data of the image, Slack/Discord doesn't like it when we make a lot of rapid requests in case you have a lot of emojis, so we get rate-limited... Hence the wait time on the first go, luckily we save all the data we need from the images (which is pretty much only the dominant colours) so we only have to run this step once.


</details>

# How to run?

### Option 1 - install the .exe - (quickest and easiest)
You can simply navigate to the release tab or go [here](https://github.com/Slowlor1ss/SlackPaint/releases)
and install the SlackPaint.exe, this one file is all you need to run the program.

---

### Option 2 - Run the Python program yourself
For this option, you will need to install/have installed Python and (preferably) added to system variables (if you don't know how to install Python, I recommend simply running the .exe)
You can simply run the `install_dependencies.bat` to install all necessary libraries
and then launch the Python file from the console using the command `python (C:\path\to\)SlackPaint.py`

# How to use this tool

This tool works by the concept that Slack emojis (and lots of other platforms like Discord, etc.) have a text representation usually in the format of a *colon text colon* like **:this:**<br>
This tool simply allows you to paint in a grid and export that grid in text form so you can send it over your platform of choice.

### Drawing patterns
- You can draw patterns by simply dragging the mouse over the grid while pressing the left mouse button, and you can erase using the right mouse button.
- You can change the colour you are painting using the number keys on your keyboard or by clicking on the name of the emoji you want to paint.
- You can add colours using the "Add Emoji button", and additionally, you can draw slack emojis using the "Add Slack Emoji button" - See ([How to import Slack emojis](#how-to-import-slack-emojis) for more info on that) remove them using the minus button next to the emoji you want to remove


# How to import Slack emojis

To import slack emojis, you will need to naviage to https://YourSlackServer.slack.com/customize/emoji or use the "**customise workspace**" button in your slack server.
<br><img src="https://github.com/user-attachments/assets/aa9b8c22-080e-4fa9-ad43-8891d593ca12" width="40%"/><br>

From here, you will need to:
1. Open DevTools (F12 or Ctrl+Shift+I)
2. In the Console tab, paste the code from [this](./ScriptToGetSlackEmojis.js) file and run it (press enter or "run" button) and wait until it finishes
3. Save the output file
4. Use this file when clicking "Add Slack Emoji" in Slack Paint

After doing these steps, you should be able to add Slack emojis by clicking the "Add Slack Emoji" button and picking what emoji you want to draw.
Doing this will also allow you to use the Image to Emoji feature.
<br><img src="https://github.com/user-attachments/assets/254830ce-612d-404d-9635-94a3ed6e66d7" width="50%"/><br>


# How can I make these mosaics/pixel art out of emojis?

To use the Image to Emoji feature, you will first need to follow the steps in [How to import Slack emojis](#how-to-import-slack-emojis)
after you've done this you will be able to use the Image to Emoji button, this should pop up a new window where you can change setting for your mosaic and upload an image that you want to recreate.
This might take a minute to generate first time you use it depending on the amount of emojis you have, after the first time it should go relativly fast.
<br><img src="https://github.com/user-attachments/assets/edc86048-0040-427c-9d83-a07bba97ea7a" width="50%"/><be>

# How to import Discord emojis

(Note: unless you have discord Nitro don't expect to be sending cool pixel art using the tool over discord, due to the small message limit your art will be very limited)

To import discord emojis, you will need to simply open discord in the browser and log in to your account that's in the server you want to scrape the emojis from.
From here, you will need to:
1. Open DevTools (F12 or Ctrl+Shift+I)
2. In the Console tab, paste the code from [this](./ScriptToGetDiscordEmojis.js) file and run it (press enter or "run" button) you can cancel this process as soon as the scrolling passed the server you want to scrape emojis from.
3. Now you should see a window that allows you to choose what server you want to scrape the emojis from, or the "all" option if you want every server's emoji (only useful for Nitro users)
4. Once you have selected a server it will scroll through that server's emojis and download the JSON file once done
5. Use this file when clicking "Add Slack Emoji" (I know I need to rename this button) in Slack Paint (and the tool...)

After doing these steps, you should be able to add Discord emojis by clicking the "Add Slack Emoji" button and picking what emoji you want to draw.
Doing this will also allow you to use the Image to Emoji feature. (Again only really useful for small art or Nitro users (Don't complain at me, complain at Discord))
