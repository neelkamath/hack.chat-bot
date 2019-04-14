#!/usr/bin/env python3

"""Connects the bot."""

import os
import os.path
import random
import re
import sys
import threading
import time

import hclib
import pymongo

from commands import currency
from commands import dictionary
from commands import jokes
from commands import katex
from commands import password
from commands import paste
from commands import poetry
from commands import search
import utility


class HackChatBot:
    """Runs the bot."""
    _charsPerLine = 88
    _maxLines = 8
    # Messages with more than <_maxChars> characters cause ratelimits.
    _maxChars = _charsPerLine * _maxLines
    _trigger = os.environ.get("TRIGGER")
    _nick = os.environ.get("NICK")
    _url = os.environ.get("URL")

    def __init__(self):
        """Initializes values."""
        # Use <os.environ.get> instead of <if KEY in os.environ> as the
        # former makes sure it isn't an empty value.
        if (not os.environ.get("CHANNELS") or not os.environ.get("NICK")
            or not os.environ.get("TRIGGER") or not os.environ.get("URL")):
            sys.exit("Please create the \"CHANNELS\", \"NICK\", \"TRIGGER\" "
                     "and \"URL\" environment variables.")
        # The features and their respective functions.
        self._commands = {
            "afk": self._away,
            "alias": self._alias,
            "define": self._define,
            "h": self._help,
            "help": self._help,
            "join": self._join,
            "joke": self._joke,
            "katex": self._generate_katex,
            "leave": self._leave,
            "msg": self._message,
            "password": self._strengthen,
            "poem": self._give_poetry,
            "poet": self._give_poetry,
            "rate": self._convert,
            "search": self._search,
            "stats": self._request_statistics,
            "toss": self._toss,
            "translate": self._translate,
            "uptime": self._check_uptime,
            "urban": self._urban_define
        }
        self._startTime = time.time()
        uri = os.environ.get("MONGODB_URI")
        client = pymongo.MongoClient(uri)
        uri = uri[::-1]
        slash = re.search(r"/", uri)
        dbName = uri[:slash.start()]
        dbName = dbName[::-1]
        self._db = client[dbName]
        env = lambda x, y: os.environ.get(x) if x in os.environ else y
        self._pwd = env("PASSWORD", "")
        self._codeUrl = env("CODE_URL", None)
        oxfordAppId = os.environ.get("OXFORD_APP_ID")
        oxfordAppKey = os.environ.get("OXFORD_APP_KEY")
        if oxfordAppId and oxfordAppKey:
            self._oxford = dictionary.Oxford(oxfordAppId, oxfordAppKey)
        else:
            self._commands.pop("define")
            self._commands.pop("translate")
        exchangeRateApiKey = os.environ.get("EXCHANGE_RATE_API_KEY")
        if exchangeRateApiKey:
            self._exchangeRateApiKey = exchangeRateApiKey
        else:
            self._commands.pop("rate")
        print("The bot will wait 30 seconds before joining each new channel "
              + "to prevent getting ratelimited.")
        self._channels = os.environ.get("CHANNELS").split(", ")
        for channel in self._channels:
            self._joinChannel(channel)
            print("The bot joined the channel {}".format(channel))
            time.sleep(30)

    def _joinChannel(self, channel):
        """Joins the hack.chat channel <channel> (<str>)."""
        args = (self._handle, self._nick, channel, self._pwd, self._url,)
        threading.Thread(target=hclib.HackChat, args=args).start()

    def _handle(self, hackChat, info):
        """Callback function for data sent from hack.chat.

        <hackChat> (callback parameter) is the connection object.
        <info> (callback parameter) is the data sent.
        """
        self._hackChat = hackChat
        self._info = info
        if self._info["type"] == "invite":
            self._joinChannel(self._info["channel"])
        elif self._info["type"] == "message":
            # Don't check for AFK statuses if the bot itself sent the
            # message. Otherwise if the bot replied to someone stating
            # chat a user is AFK, the bot will reply to its own message
            # as the AFK user was mentioned in that message.
            if self._nick != self._info["nick"]:
                self._check_afk()
            self._post()
            if "trip" in self._info:
                self._log_trip_code()
            txt = self._info["text"].strip()
            space = re.search(r"\s", txt)
            self._msg = txt[space.end():].strip() if space else None
            call = txt[:len(self._trigger)]
            if call == self._trigger:
                check = space.start() if space else len(txt)
                self._cmd = txt[len(self._trigger):check]
                # Get the requested feature (e.g., katex:red is katex).
                pattern = re.search(r"[^a-zA-Z]", self._cmd)
                area = pattern.start() if pattern else len(txt)
                self._feature = self._cmd[:area]
                if self._feature in self._commands:
                    self._commands[self._feature]()
        elif self._info["type"] == "online add":
            self._post()
        elif self._info["type"] == "online remove":
            field = "{}.{}".format(self._hackChat.channel, self._info["nick"])
            self._db["afk"].update_one(
                {
                    self._hackChat.channel: {
                        "$exists": True
                    }
                },
                {
                    "$unset": {
                        field: ""
                    }
                }
            )
        elif self._info["type"] == "stats":
            self._hackChat.send(
                "There are {} unique IPs in ".format(self._info["IPs"])
                + "{} channels.".format(self._info["channels"]))
        elif self._info["type"] == "warn":
            print(self._info["warning"])

    def _check_afk(self):
        """Notifies AFK statuses.

        Checks incoming messages for users @-mentioning users who are
        AFK. If it finds any, it will notify them of such.
        """
        collection = self._db["afk"]
        query = {
            self._hackChat.channel: {
                "$exists": True
            }
        }
        doc = collection.find_one(query)
        if not doc:
            return
        field = "{}.{}".format(self._hackChat.channel, self._info["nick"])
        collection.update_one(
            query,
            {
                "$unset": {
                    field: ""
                }
            }
        )
        reply = ""
        users = doc[self._hackChat.channel]
        for field in users:
            # Keep a space around the name so as to make sure names
            # nested in longer words aren't taken by accident (e.g.,
            # "bot" in "mybot").
            person = " @{} ".format(field)
            # Add a space around the message so as to account for
            # <person>'s extra spaces.
            if person in " {} ".format(self._info["text"].strip()):
                reply += person.strip()
                reason = users[field]
                if reason:
                    reply += ": {}".format(reason)
                reply += "\n"
        if reply:
            self._hackChat.send(
                "@{} AFK users:\n{}".format(self._info["nick"], reply))

    def _log_trip_code(self):
        """Stores nicknames with their trip codes."""
        self._db["trip_codes"].update_one(
            {
                self._info["trip"]: {
                    "$exists": True
                }
            },
            {
                "$addToSet": {
                    self._info["trip"]: self._info["nick"]
                }
            },
            upsert=True
        )

    def _post(self):
        """Sends messages saved for users."""
        collection = self._db["messages"]
        field = "{}.{}".format(self._hackChat.channel, self._info["nick"])
        query = {
            field: {
                "$exists": True
            }
        }
        doc = collection.find_one(query)
        collection.update_one(
            query,
            {
                "$unset": {
                    field: ""
                }
            }
        )
        if doc:
            reply = ""
            for msg in doc[self._hackChat.channel][self._info["nick"]]:
                reply += "@{}: {}\n".format(msg["sender"], msg["message"])
            self._hackChat.send(
                "@{} you have messages:\n{}".format(self._info["nick"], reply))

    def _alias(self):
        """Sends the requested trip code's holdees."""
        if self._msg:
            doc = self._db["trip_codes"].find_one({
                self._msg: {
                    "$exists": True
                }
            })
            if doc:
                nicks = ", ".join(doc[self._msg])
                if len(nicks) > self._maxChars:
                    data = paste.dpaste("\n".join(doc[self._msg]))
                    if data["type"] == "success":
                        nicks = data["data"]
                    else:
                        self._hackChat.send("Sorry, I couldn't get it.")
                        return
                self._hackChat.send(
                        "@{} {} has the ".format(self._info["nick"], self._msg)
                        + "aliases {}".format(nicks))
            else:
                self._hackChat.send(
                    "@{} no aliases were found".format(self._info["nick"]))
        else:
            self._hackChat.send(
                "@{} tells the trip codes' aliases ".format(self._info["nick"])
                + "(e.g., {}alias dIhdzE)".format(self._trigger))

    def _away(self):
        """Handles AFK statuses."""
        field = "{}.{}".format(self._hackChat.channel, self._info["nick"])
        self._db["afk"].update_one(
            {
                self._hackChat.channel: {
                    "$exists": True
                }
            },
            {
                "$set": {
                    field: self._msg
                }
            },
            True
        )
        reply = "@{} is now AFK".format(self._info["nick"])
        if self._msg:
            reply += ": {}".format(self._msg)
        self._hackChat.send(reply)

    def _check_uptime(self):
        """Tells the bot's uptime."""
        diff = time.time() - self._startTime
        oneSecond = 1
        oneMinute = oneSecond * 60
        oneHour = oneMinute * 60
        oneDay = oneHour * 24
        timeTypes = {
            "days": {
                "length": oneDay,
                "count": 0
            },
            "hours": {
                "length": oneHour,
                "count": 0
            },
            "minutes": {
                "length": oneMinute,
                "count": 0
            },
            "seconds": {
                "length": oneSecond,
                "count": 0
            }
        }
        times = []
        for timeType in timeTypes:
            length = timeTypes[timeType]["length"]
            count = timeTypes[timeType]["count"]
            while diff > length:
                count += 1
                diff -= length
            if count:
                # Check if time is singular (e.g., "1 days" to "1 day").
                name = timeType[:len(timeType) - 1] if count == 1 else timeType
                times.append("{} {}".format(count, name))
        times = ", ".join(times)
        self._hackChat.send("@{} {}".format(self._info["nick"], times))

    def _convert(self):
        """Handles currency conversion."""
        converted = False
        data = self._cmd.split(":") if ":" in self._cmd else None
        if data and len(data) == 3:
            fromCode = data[1].upper()
            toCode = data[2].upper()
            if fromCode and toCode:
                data = currency.convert(self._exchangeRateApiKey, fromCode,
                                        toCode)
                if data["type"] == "success":
                    converted = True
                    self._hackChat.send(
                        "@{} 1 {} = ".format(self._info["nick"], fromCode)
                        + "{} {}".format(data["response"], toCode))
        if not converted:
            self._hackChat.send(
                "@{} Sorry, I couldn't convert ".format(self._info["nick"])
                + "that. (e.g., {}rate:usd:inr ".format(self._trigger)
                + "gives 1 USD = 64 INR)")

    def _define(self):
        """Handles definitions."""
        if self._msg:
            data = self._oxford.define(self._msg)
            if data["type"] == "success":
                self._hackChat.send(
                    "@{} {}: ".format(self._info["nick"], self._msg)
                    + data["response"])
            else:
                self._hackChat.send(
                    "@{} Sorry, I couldn't find ".format(self._info["nick"])
                    + "any definitions for that.")
        else:
            self._hackChat.send(
                "@{} e.g., {}".format(self._info["nick"], self._trigger)
                + "define hello")

    def _generate_katex(self):
        """Handles KaTeX."""
        colors = ["red", "orange", "green", "blue", "pink", "purple", "gray",
                  "rainbow"]
        sizes = ["tiny", "scriptsize", "footnotesize", "small", "normalsize",
                 "large", "Large", "LARGE", "huge", "Huge"]
        fonts = ["mathrm", "mathit", "mathbf", "mathsf", "mathtt", "mathbb",
                 "mathcal", "mathfrak", "mathscr"]
        if self._msg:
            disallowed = ("#", "$", "%", "&", "_", "{", "}", "\\", "?")
            if set(self._msg).isdisjoint(disallowed):
                data = self._cmd.split(".")
                stringify = lambda value: value if value else ""
                size = stringify(utility.identical_item(data, sizes))
                color = stringify(utility.identical_item(data, colors))
                font = stringify(utility.identical_item(data, fonts))
                txt = utility.remove_emoji(self._msg)
                txt = katex.generator(txt, size, color, font)
                self._hackChat.send(
                    "@{} says {}".format(self._info["nick"], txt))
            else:
                invalid = "\"{}\"".format("\", \"".join(disallowed))
                self._hackChat.send(
                    "@{} KaTeX doesn't support ".format(self._info["nick"])
                    + invalid)
        else:
            reply = ("@{} stylizes text (e.g., ".format(self._info["nick"])
                     + self._trigger
                     + "katex.rainbow.huge bye)\n")
            reply += "OPTIONAL COLORS: {}\n".format(", ".join(colors))
            reply += "OPTIONAL SIZES: {}\n".format(", ".join(sizes))
            reply += "OPTIONAL FONTS: {}\n".format(", ".join(fonts))
            self._hackChat.send(reply)

    def _give_poetry(self):
        """Handles poetry."""
        if self._msg:
            isPoet = True if self._cmd == "poet" else False
            data = poetry.poems(self._msg, isPoet)
            if data:
                rand = random.SystemRandom()
                data = data[rand.randrange(len(data))]
                header = "{} by {}".format(data["title"], data["author"])
                if len(header) > 100:
                    header = "{}...".format(header[:97])
                pasted = paste.dpaste(data["poem"], title=header)
                linked = "Read the rest at {}".format(pasted["data"])
                reply = ("@{} {}\n".format(self._info["nick"], data["title"])
                         + "By: {}\n{}".format(data["author"], data["poem"]))
                cut = utility.shorten_lines(reply, self._charsPerLine,
                                            self._maxLines - 1)
                self._hackChat.send(cut + linked)
            else:
                reply = "@{} Sorry, I couldn't find any poems for that."
                self._hackChat.send(reply.format(self._info["nick"]))
        else:
            if self._cmd == "poem":
                self._hackChat.send(
                    "@{} finds a poem by its name ".format(self._info["nick"])
                    + "(e.g., {}poem sonnet)".format(self._trigger))
            else:
                self._hackChat.send(
                    "@{} finds a poem from a poet ".format(self._info["nick"])
                    + "(e.g., {}poet shakespeare)".format(self._trigger))

    def _help(self):
        """Sends a message on how to use the bot."""
        joinWith = " {}".format(self._trigger)
        reply = joinWith.join(sorted(self._commands))
        reply = self._trigger + reply
        if self._codeUrl:
            reply += "\nsource code: {}".format(self._codeUrl)
        self._hackChat.send("@{} {}".format(self._info["nick"], reply))

    def _join(self):
        """Joins a channel."""
        if self._msg:
            self._joinChannel(self._msg)
        else:
            self._hackChat.send(
                "@{} joins a hack.chat channel ".format(self._info["nick"])
                + "(e.g., {}join ben)\nYou can also ".format(self._trigger)
                + "invite the bot via the sidebar.")

    def _joke(self):
        """Sends jokes."""
        joke = jokes.yo_momma()
        self._hackChat.send("@{} {}".format(self._info["nick"], joke))

    def _leave(self):
        """Leaves the channel currently connected to if allowed."""
        if self._hackChat.channel in self._channels:
            self._hackChat.send("I cannot leave this channel.")
        else:
            self._hackChat.leave()

    def _message(self):
        """Saves messages to send to users when they're next active."""
        info = self._cmd.split(":")
        if len(info) == 2 and info[1] and self._msg:
            self._db["messages"].update_one(
                {
                    self._hackChat.channel: {
                        "$exists": True
                    }
                },
                {
                    "$addToSet": {
                        "{}.{}".format(self._hackChat.channel, info[1]): {
                            "sender": self._info["nick"],
                            "message": self._msg
                        }
                    }
                },
                True
            )
            self._hackChat.send(
                "@{}, @{} will get your ".format(self._info["nick"], info[1])
                + "message the next time they message or join a channel.")
        else:
            self._hackChat.send(
                "@{} sends a message to a user the ".format(self._info["nick"])
                + "next time they send a message or join a channel (e.g., "
                + "{}msg:ben how are you?)".format(self._trigger))

    def _request_statistics(self):
        """Requests statistics."""
        self._hackChat.stats()

    def _search(self):
        """Handles searches."""
        if self._msg:
            results = search.duckduckgo(self._msg, "hack.chat bot")
            reply = ""
            if results["URL"]:
                reply += "{} ".format(results["URL"])
            if results["Heading"]:
                reply += "{}: ".format(results["Heading"])
            if results["Answer"]:
                reply += results["Answer"]
            elif results["AbstractText"]:
                reply += results["AbstractText"]
            else:
                reply = ""
            tell = "@{} ".format(self._info["nick"])
            reply = utility.shorten(reply, self._maxChars - len(tell), ".")
            if not reply:
                reply = "Sorry, I couldn't find anything."
            self._hackChat.send(tell + reply)
        else:
            self._hackChat.send(
                "@{} instant answers (e.g., ".format(self._info["nick"])
                + "{}search pokemon ruby)".format(self._trigger))

    def _strengthen(self):
        """Handles passwords."""
        if self._msg:
            pwd = password.strengthen(self._msg)
            self._hackChat.send("@{} {}".format(self._info["nick"], pwd))
        else:
            self._hackChat.send(
                "@{} strengthens a password (e.g., ".format(self._info["nick"])
                + "{}password gum)".format(self._trigger))

    def _toss(self):
        """Handles coin tosses."""
        rand = random.SystemRandom()
        result = "heads" if rand.randrange(2) else "tails"
        self._hackChat.send("@{} {}".format(self._info["nick"], result))

    def _translate(self):
        """Handles translations."""
        languages = {"english": "en",
                     "spanish": "es",
                     "pedi": "nso",
                     "romanian": "ro",
                     "malay": "ms",
                     "zulu": "zu",
                     "indonesian": "id",
                     "tswana": "tn"}
        explain = True
        if self._msg and len(re.findall(":", self._cmd)) == 2:
            data = self._cmd.lower().split(":")
            if data[1] in languages and data[2] in languages:
                explain = False
                srcLang = languages[data[1]]
                targetLang = languages[data[2]]
                words = self._msg.split()
                translations = []
                for word in words:
                    word = re.sub(r"[^a-zA-Z]", "", word)
                    word = self._oxford.translate(word, targetLang, srcLang)
                    if word["type"] == "failure":
                        translations = []
                        break
                    translations.append(word["response"])
                if translations:
                    translated = " ".join(translations)
                    self._hackChat.send(
                        "@{} {}".format(self._info["nick"], translated))
                else:
                    self._hackChat.send(
                        "@{} Sorry, I couldn't ".format(self._info["nick"])
                        + "translate it all.")
        if explain:
            self._hackChat.send(
                "@{} supported languages: ".format(self._info["nick"])
                + "{}\ne.g., ".format(", ".join(languages.keys()))
                + "{}".format(self._trigger)
                + "translate:english:spanish I have a holiday!\n")

    def _urban_define(self):
        """Handles urban definitions."""
        if self._msg:
            data = dictionary.urban(self._msg)
            if data:
                reply = "@{} {}: {} ".format(self._info["nick"], data["word"],
                                             data["definition"])
                reply = utility.shorten_lines(reply, self._charsPerLine,
                                              self._maxLines - 1)
                self._hackChat.send(reply + data["permalink"])
            else:
                self._hackChat.send(
                    "@{} Sorry, I couldn't find ".format(self._info["nick"])
                    + "any definitions for that.")
        else:
            self._hackChat.send(
                "@{} searches Urban Dictionary ".format(self._info["nick"])
                + "(e.g., {}urban covfefe)".format(self._trigger))


if __name__ == "__main__":
    HackChatBot()
