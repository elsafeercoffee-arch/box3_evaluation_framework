import re

ARABIC_DIACRITICS = re.compile(r"[\u0617-\u061A\u064B-\u0652\u0670]")
TATWEEL = "\u0640"
PUNCT = re.compile(r"[^\w\s]|_")

STOPWORDS = {
    "في", "من", "على", "إلى", "عن", "مع", "هل", "ما", "هي", "هو",
    "كم", "متى", "أين", "كيف", "لماذا", "أن", "إن", "كان", "يكون",
    "هذا", "هذه", "ذلك", "تلك", "التي", "الذي", "أو", "و", "ثم",
    "لا", "لم", "لن", "قد", "كل", "بعض", "بين", "عند", "بعد", "قبل",
}


def normalize_arabic(text: str) -> str:
    if not text:
        return ""
    text = ARABIC_DIACRITICS.sub("", text).replace(TATWEEL, "")
    text = re.sub(r"[أإآٱ]", "ا", text)
    text = text.replace("ى", "ي").replace("ة", "ه")
    digits = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    text = text.translate(digits)
    text = PUNCT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def extract_tokens(text: str) -> set:
    norm = normalize_arabic(text)
    return {t for t in norm.split() if len(t) > 1 and t not in STOPWORDS}
