import json
import os
import urllib.parse
import urllib.request


BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def telegram_request(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    data = urllib.parse.urlencode(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


message = """🔥 GETBYTERUSH DAILY

META PLANNED TO CUT SOME
TEAMS BY 60%

Then something went wrong.

━━━━━━━━━━━━━━━━━━

Story Score: 9.2/10

Curiosity:     9/10
Story:        10/10
Shareability:  9/10
Visual:       10/10

━━━━━━━━━━━━━━━━━━

#MetaAI #AI #ArtificialIntelligence
#FutureOfWork #TechNews

This is a TEST approval post.
"""


keyboard = {
    "inline_keyboard": [
        [
            {
                "text": "👀 PREVIEW",
                "callback_data": "preview:test-meta"
            }
        ],
        [
            {
                "text": "✅ APPROVE & POST",
                "callback_data": "approve:test-meta"
            },
            {
                "text": "❌ REJECT",
                "callback_data": "reject:test-meta"
            }
        ]
    ]
}


response = telegram_request(
    "sendMessage",
    {
        "chat_id": CHAT_ID,
        "text": message,
        "reply_markup": json.dumps(keyboard),
    },
)

print(json.dumps(response, indent=2))