"""
content_bank.py
==================

Design decision worth explaining: Requirement 7 caps conversation context
at the 6 most recent messages, which means the LLM itself CANNOT reliably
remember which riddles/questions it already asked once a session runs
past 3 exchanges -- the earlier ones simply fall out of its context
window. Relying on the model's own memory to satisfy "no repeating
riddles within the same session" would therefore be fundamentally
unreliable.

Instead, this module holds a fixed, curated bank of riddles and quiz
questions. The SESSION STORE (not the LLM) tracks which indices have
already been used per session, guaranteeing no repeats regardless of how
long the conversation context window is. The LLM is still very much in
the loop -- it generates the actual warm, encouraging, varied DELIVERY
text around this fixed content (see prompts.py) -- but the content
selection and correctness grading are deterministic and testable.
"""

import random

# --------------------------------------------------------------------------- #
# Brain Buster: riddles
# --------------------------------------------------------------------------- #
# Each entry: riddle text, a list of acceptable answers (lowercase, for
# normalized matching), and exactly 3 progressively more revealing hints.

RIDDLES = [
    {
        "riddle": "I have keys but no locks. I have space but no room. You can enter, but you can't go outside. What am I?",
        "answers": ["keyboard", "a keyboard"],
        "hints": [
            "You probably use me every day if you use a computer.",
            "I have letters, numbers, and a spacebar.",
            "You type on me!",
        ],
    },
    {
        "riddle": "The more you take, the more you leave behind. What am I?",
        "answers": ["footsteps", "footprints", "steps"],
        "hints": [
            "Think about walking somewhere new, like sand or snow.",
            "You make these with your feet.",
            "They're the marks your shoes leave behind you as you walk.",
        ],
    },
    {
        "riddle": "What has a face and two hands but no arms or legs?",
        "answers": ["clock", "a clock", "watch", "a watch"],
        "hints": [
            "You look at me to know something important.",
            "I help you know what time it is.",
            "I tick and have numbers from 1 to 12.",
        ],
    },
    {
        "riddle": "What gets wetter the more it dries?",
        "answers": ["towel", "a towel"],
        "hints": [
            "You use me after a bath or shower.",
            "I'm soft and fluffy and hang in the bathroom.",
            "You use me to dry yourself off, but I get wet doing it!",
        ],
    },
    {
        "riddle": "What has to be broken before you can use it?",
        "answers": ["egg", "an egg"],
        "hints": [
            "You might have this for breakfast.",
            "It comes from a chicken.",
            "You crack its shell before cooking it!",
        ],
    },
    {
        "riddle": "I'm tall when I'm young and short when I'm old. What am I?",
        "answers": ["candle", "a candle"],
        "hints": [
            "You might see me on a birthday cake.",
            "I can make light in the dark.",
            "I have a flame and I melt as I burn!",
        ],
    },
    {
        "riddle": "What has many teeth but cannot bite?",
        "answers": ["comb", "a comb"],
        "hints": [
            "You use me to fix your hair.",
            "I have thin, straight teeth in a row.",
            "You run me through your hair to make it neat!",
        ],
    },
    {
        "riddle": "What can travel all around the world while staying in one corner?",
        "answers": ["stamp", "a stamp", "postage stamp"],
        "hints": [
            "You'd find me on an envelope.",
            "I help letters travel far away.",
            "I'm small, sticky, and go in the corner of an envelope!",
        ],
    },
    {
        "riddle": "What has a neck but no head?",
        "answers": ["bottle", "a bottle"],
        "hints": [
            "You might drink from me.",
            "I can be made of glass or plastic.",
            "I hold water or juice, and I have a narrow top called a neck!",
        ],
    },
    {
        "riddle": "What kind of room has no doors or windows?",
        "answers": ["mushroom", "a mushroom"],
        "hints": [
            "I'm hiding inside a word you already know.",
            "Think about the ending of the word 'room'.",
            "I grow in forests and the word contains 'mush'!",
        ],
    },
    {
        "riddle": "What has one eye but cannot see?",
        "answers": ["needle", "a needle"],
        "hints": [
            "You might find me in a sewing kit.",
            "Thread goes through my 'eye.'",
            "I'm thin, sharp, and used for sewing!",
        ],
    },
    {
        "riddle": "What goes up but never comes down?",
        "answers": ["age", "your age"],
        "hints": [
            "Everyone has this, and it changes every year.",
            "You celebrate it on your birthday.",
            "It's how old you are -- it only ever increases!",
        ],
    },
]


# --------------------------------------------------------------------------- #
# Quick Fire: trivia questions, spanning the 7 required topics
# --------------------------------------------------------------------------- #
# Each entry: topic, question text, accepted answers, and a short
# educational fact delivered after a CORRECT answer.

QUICK_FIRE_QUESTIONS = [
    # Science
    {"topic": "science", "question": "What gas do humans need to breathe to stay alive?",
     "answers": ["oxygen"], "correct_answer_display": "Oxygen",
     "fact": "Oxygen makes up about 21% of the air around us!"},
    {"topic": "science", "question": "What is the closest planet to the Sun?",
     "answers": ["mercury"], "correct_answer_display": "Mercury",
     "fact": "Mercury is so close to the Sun that a year there is only 88 Earth days long!"},
    {"topic": "science", "question": "What part of the plant makes food using sunlight?",
     "answers": ["leaf", "leaves"], "correct_answer_display": "Leaves",
     "fact": "This process is called photosynthesis, and it also makes the oxygen we breathe!"},

    # Mathematics
    {"topic": "mathematics", "question": "What is 7 plus 8?",
     "answers": ["15", "fifteen"], "correct_answer_display": "15",
     "fact": "Fun fact: 15 is also the number of pieces in a standard checkers set for one player!"},
    {"topic": "mathematics", "question": "How many sides does a hexagon have?",
     "answers": ["6", "six"], "correct_answer_display": "6",
     "fact": "Honeycomb cells made by bees are hexagons -- it's the most efficient shape for packing!"},
    {"topic": "mathematics", "question": "What number comes right after 99?",
     "answers": ["100", "one hundred"], "correct_answer_display": "100",
     "fact": "100 is called a 'century' -- that's why 100 years is called a century too!"},

    # Geography
    {"topic": "geography", "question": "What is the largest continent on Earth?",
     "answers": ["asia"], "correct_answer_display": "Asia",
     "fact": "Asia is home to more than half of all the people on Earth!"},
    {"topic": "geography", "question": "What is the longest river in the world?",
     "answers": ["nile", "the nile"], "correct_answer_display": "The Nile",
     "fact": "The Nile River flows through 11 different countries in Africa!"},
    {"topic": "geography", "question": "What do we call a large area of land completely surrounded by water?",
     "answers": ["island", "an island"], "correct_answer_display": "An island",
     "fact": "The largest island in the world is Greenland!"},

    # English
    {"topic": "english", "question": "What do we call a word that means the opposite of another word?",
     "answers": ["antonym", "an antonym"], "correct_answer_display": "Antonym",
     "fact": "'Hot' and 'cold' are antonyms of each other!"},
    {"topic": "english", "question": "What punctuation mark do we use at the end of a question?",
     "answers": ["question mark", "?"], "correct_answer_display": "A question mark (?)",
     "fact": "The question mark is thought to come from an old Latin word 'quaestio' meaning 'question'!"},
    {"topic": "english", "question": "What do we call a word that sounds the same as another word but has a different meaning, like 'sea' and 'see'?",
     "answers": ["homophone", "a homophone"], "correct_answer_display": "Homophone",
     "fact": "English has hundreds of homophones -- 'flower' and 'flour' are another example!"},

    # Animals
    {"topic": "animals", "question": "What is the largest animal in the world?",
     "answers": ["blue whale", "whale"], "correct_answer_display": "The blue whale",
     "fact": "A blue whale's heart alone can weigh as much as a small car!"},
    {"topic": "animals", "question": "How many legs does a spider have?",
     "answers": ["8", "eight"], "correct_answer_display": "8",
     "fact": "Spiders are not insects -- insects have 6 legs, but spiders are arachnids with 8!"},
    {"topic": "animals", "question": "What do we call a baby dog?",
     "answers": ["puppy", "a puppy"], "correct_answer_display": "A puppy",
     "fact": "A group of puppies from the same birth is called a 'litter'!"},

    # Space
    {"topic": "space", "question": "What is the name of the galaxy that contains our Solar System?",
     "answers": ["milky way", "the milky way"], "correct_answer_display": "The Milky Way",
     "fact": "The Milky Way has over 100 billion stars -- and our Sun is just one of them!"},
    {"topic": "space", "question": "What do we call a person who travels into space?",
     "answers": ["astronaut", "an astronaut"], "correct_answer_display": "An astronaut",
     "fact": "The first astronaut to walk on the Moon was Neil Armstrong, in 1969!"},
    {"topic": "space", "question": "Which planet is known as the Red Planet?",
     "answers": ["mars"], "correct_answer_display": "Mars",
     "fact": "Mars looks red because its soil contains a lot of iron oxide -- the same thing that makes rust red!"},

    # General knowledge
    {"topic": "general knowledge", "question": "How many days are there in a leap year?",
     "answers": ["366"], "correct_answer_display": "366",
     "fact": "Leap years happen almost every 4 years to keep our calendar matched up with Earth's orbit!"},
    {"topic": "general knowledge", "question": "What do bees make that people like to eat?",
     "answers": ["honey"], "correct_answer_display": "Honey",
     "fact": "Honey never spoils -- archaeologists have found edible honey in ancient Egyptian tombs!"},
    {"topic": "general knowledge", "question": "What is the tallest mountain in the world?",
     "answers": ["mount everest", "everest"], "correct_answer_display": "Mount Everest",
     "fact": "Mount Everest is still growing a tiny bit taller every year due to shifting tectonic plates!"},
]


def normalize_answer(text: str) -> str:
    """Lowercases, strips whitespace/punctuation for lenient answer comparison -- generous with kids' spelling and phrasing, since a rigid exact-match would be frustrating for the target audience."""
    cleaned = text.strip().lower()
    for ch in ".,!?'\"":
        cleaned = cleaned.replace(ch, "")
    return cleaned.strip()


def is_answer_correct(user_answer: str, accepted_answers: list) -> bool:
    """Checks a user's normalized answer against a list of accepted normalized answers, allowing a loose substring match in either direction for short answers (helps with e.g. 'an egg' vs 'egg')."""
    normalized_user = normalize_answer(user_answer)
    if not normalized_user:
        return False
    for accepted in accepted_answers:
        normalized_accepted = normalize_answer(accepted)
        if normalized_user == normalized_accepted:
            return True
        if len(normalized_accepted) <= 20 and (
            normalized_accepted in normalized_user or normalized_user in normalized_accepted
        ):
            return True
    return False


def pick_unused_riddle(used_indices: set):
    """Returns (index, riddle_dict) for a random riddle not yet used this session, or (None, None) if the whole bank has been used."""
    available = [i for i in range(len(RIDDLES)) if i not in used_indices]
    if not available:
        return None, None
    idx = random.choice(available)
    return idx, RIDDLES[idx]


def pick_unused_question(used_indices: set):
    """Returns (index, question_dict) for a random Quick Fire question not yet used this session, or (None, None) if the whole bank has been used."""
    available = [i for i in range(len(QUICK_FIRE_QUESTIONS)) if i not in used_indices]
    if not available:
        return None, None
    idx = random.choice(available)
    return idx, QUICK_FIRE_QUESTIONS[idx]
