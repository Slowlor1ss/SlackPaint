<details open>
<summary><strong>Table of Contents</strong></summary>

- [How to run?](#how-to-run)
  - [Option 1 - install the .exe](#option-1---install-the-exe---quickest-and-easiest)
  - [Option 2 - Run the Python program yourself](#option-2---run-the-python-program-yourself)
- [How to use this tool](#how-to-use-this-tool)
  - [Drawing patterns](#drawing-patterns)
- [How to import Slack emojis](#how-to-import-slack-emojis)
- [How can I make these mosaics/pixel art out of emojis?](#how-can-i-make-these-mosaicspixel-art-out-of-emojis)

</details>

# How to run?

### Option 1 - install the .exe - (quickest and easiest)
You can simply navigate to the release tab or go [here](https://github.com/Slowlor1ss/SlackPaint/releases)
and istall the SlackPaint.exe this one file is all you need to run the program.

---

### Option 2 - Run the Python program yourself
For this option, you will need to install/have installed Python
you can simple run the `install_dependencies.bat` to install all necessery libraries
and then lauch the the python file from comnsole using the command `python (C:\path\to\)SlackPaint.py`

# How to use this tool

This tool works by the concept that Slack emojis (and lots of other platforms like Discord, etc.) have a text representation usually in the format of a *colon text colon* like **:this:**<br>
This tool simply allows you to paint in a grid and export that grid in text form so you can send it over your platform of choice.

### Drawing patterns
- You can draw patterns by simply dragging the mouse over the grid while pressing the left mouse button, and you can erase using the right mouse button.
- You can change the colour you are painting using the number keys on your keyboard or by clicking on the name of the emoji you want to paint.
- You can add colours using the "Add Emoji button", and additionally, you can draw slack emojis using the "Add Slack Emoji button" - See ([How to import Slack emojis](#how-to-import-slack-emojis) for more info on that) remove them using the minus button next to the emoji you want to remove


# How to import Slack emojis

(Note: unfortunately for now I only have a simple way of importing Slack emojis, not for any other platform like Discord, but it is possible for you to add this functionality yourself.)

To import slack emojis, you will need to naviage to https://YourSlackServer.slack.com/customize/emoji or use the "**customise workspace**" button in your slack server.
<br><img src="https://github.com/user-attachments/assets/aa9b8c22-080e-4fa9-ad43-8891d593ca12" width="40%"/><br>

From here, you will need to:
1. Open DevTools (F12 or Ctrl+Shift+I)
2. In the Console tab, paste the code from [this](./ScriptToGetSlackEmojis.js) file and run it (press enter or "run" button) and wait until it finishes
3. Save the output file
4. Use this file when clicking "Add Slack Emoji" in Slack Paint

After doing these steps, you should be able to add Slack emojis by clicking the "Add Slack Emoji" button and picking what emoji you want to draw.
Doing this will also allow you to use the Image to Emoji feature.

# How can I make these mosaics/pixel art out of emojis?

To use the Image to Emoji feature you will first need to follow the steps in [How to import Slack emojis](#how-to-import-slack-emojis)
after you've done this you will be able to use the Image to Emoji button, this should pop up a new window where you can change setting for your mosaic and upload a image that you want to recreate.
This might take a minute to generate first time you use it depending on the amount of emojis you have, after the first time it should go relativly fast.


