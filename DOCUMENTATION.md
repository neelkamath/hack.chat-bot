# Using features

When accessing features, prefix the command with the bot's trigger.

|feature  |syntax                                                      |example                                    |
|---------|------------------------------------------------------------|-------------------------------------------|
|afk      |afk `<OPTIONAL REASON>`                                     |afk eating breakfast                       |
|alias    |alias `<TRIP CODE>`                                         |alias dIhdzE                               |
|define   |define `<WORD>`                                             |define hello                               |   
|h        |h                                                           |                                           |
|help     |help                                                        |                                           |
|join     |join `<CHANNEL>`                                            |join hacking                               |
|joke     |joke                                                        |                                           |
|katex    |katex.`<OPTIONAL COLOR>`.`<OPTIONAL SIZE>`.`<OPTIONAL FONT>`|katex.green.large.mathbf                   |
|leave    |leave                                                       |                                           |
|msg      |msg:`<RECEIVER>` `<MESSAGE>`                                |msg:henry do you know javascript?          |
|password |password `<PASSWORD TO STRENGTHEN>`                         |password Ninja!                            |
|poem     |poem `<TITLE>`                                              |poem sonnet                                |
|poet     |poet `<AUTHOR>`                                             |poet shakespeare                           |
|rate     |rate:`<CURRENCY IN QUESTION>`:`<CURRENCY FOR RATE>`         |rate:usd:inr                               |
|search   |search `<QUERY>`                                            |search pokemon ruby                        |
|stats    |stats                                                       |                                           |
|toss     |toss                                                        |                                           |
|translate|translate:`<FROM>`:`<TO>`                                   |translate:english:spanish I have a holiday!|
|uptime   |uptime                                                      |                                           |
|urban    |urban `<PHRASE>`                                            |urban covfefe                              |

# Database Design

Data is stored in MongoDB.

Data may be stored organized by channels to prevent the transfer of incorrect data in the case of two different users having the same nickname in different channels.

## afk

This collection is used to help notify users @-mentioning users who are AFK that they are AFK. This feature would be used by users who are unable to participate in the channel at the time but would like to see the messages that were exchanged while they were gone as leaving the channel clears messages on hack.chat.

### Format

```
Document(s): channel's name (<string>): {
    "nickname": "reason (<string>) or no reason (<null>)"
}
```

### Example

```
Document: {
    "programming": {
        "john": "having breakfast",
        "carl": null
    }
}
Document: {
    "botDev": {
        "Roger": "on a phone call"
    }
}
```

## messages

This collection stores messages for users who are currently not available.

### Format

```
Document(s): {
    "<channel's name>": {
        "receiver": [
            {
                "sender": "nickname",
                "message": "message"
            }
        ]
    }
}
```

### Example

```
Document: {
    "programming": {
        "chris": [
            {
                "sender": "roger",
                "message": "do you know javascript?"
            },
            {
                "sender": "jacob",
                "message": "do you play call of duty?"
            }
        ]
    }
}
Document: {
    "hacking": {
        "ryan": [
            {
                "sender": "barney",
                "message": "do i need to know bash?"
            }
        ],
        "rob": [
            {
                "sender": "rahul",
                "message": "i finished learning powershell!"
            },
            {
                "sender": "bob",
                "message": "yes, i use a VPS"
            }
        ]
    }
}
```

## trip_codes:

This collection is used to help check whether a user is who they
say they are.

### Format

```
Document(s): {
    "<tripCode>": [
        "<associated nickname>"
    ]
}
```

### Example

```
Document: {
    "dIhdzE": [
        "neel",
        "neel_android"
    ]
}

Document: {
    "j8Ulk7": [
        "owl"
    ]
}
```
