import unicodedata


def normalize_answer(text):
    text=unicodedata.normalize("NFC",text).translate(str.maketrans({"’":"'","ʼ":"'","‘":"'"}))
    return " ".join(text.casefold().split())
