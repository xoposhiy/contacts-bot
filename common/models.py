import itertools
import re
import unicodedata
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class Course(BaseModel):
    code: str
    title: str
    grade: Optional[int] = None # 0..100


NAME_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿĀ-žḀ-ẕ'’-]+")

def normalize(s: str) -> str:
    # Unicode-normalize, lowercase, strip extra spaces/quotes/dashes
    s = unicodedata.normalize("NFKC", s).lower().strip()
    # Replace fancy apostrophes/dashes with plain ones for consistency
    s = s.replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
    return s

def tokenize_names(*parts: str) -> List[str]:
    tokens: List[str] = []
    seen = set()
    for part in parts:
        if not part:
            continue
        part = normalize(part)
        for m in NAME_TOKEN_RE.findall(part):
            t = m.strip("-'")  # drop leading/trailing punctuation
            if not t:
                continue
            if t not in seen:
                seen.add(t)
                tokens.append(t)
    return tokens

def generate_ordered_pairs(tokens: List[str]) -> List[str]:
    # ordered pairs of distinct tokens
    return [f"{a} {b}" for a, b in itertools.permutations(tokens, 2)]

class Student(BaseModel):
    first_name: str
    last_name: str
    name_pairs: List[str] = Field(default_factory=list)  # <-- Firestore array
    cub_email: str
    personal_email: str
    telegram_name: str
    telegram_id: int
    admission_year: int
    scholarship: str
    citizenship: str
    public_comment: str = ""
    secret_comment: str = ""
    matric_number: Optional[str] = None
    # courses: List["Course"] = Field(default_factory=list)  # assuming Course exists

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @model_validator(mode="after")
    def build_name_pairs(self):
        # Only auto-fill if not supplied explicitly
        if not self.name_pairs:
            tokens = tokenize_names(self.first_name, self.last_name)
            # If you also want to include known aliases, add them to tokenize_names() here.
            self.name_pairs = generate_ordered_pairs(tokens)
        return self


class FieldDesc(BaseModel):
    name: str
    type: str
    description: str
    aliases: List[str] = Field(default_factory=list)
