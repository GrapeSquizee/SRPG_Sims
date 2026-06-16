"""Agent definitions for the SRPG Sims prototype."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random
from typing import Iterable


@dataclass(frozen=True)
class AgentResponse:
    """A single agent's contribution to the debate."""

    agent: str
    role: str
    proposal: str
    effect: dict[str, int]
    tags: tuple[str, ...]


@dataclass(frozen=True)
class WorldAgent:
    """An interactable world element that can join a multi-agent debate."""

    name: str
    role: str
    temperament: str
    verbs: tuple[str, ...]
    stat_bias: str

    def respond(self, prompt: str, memory_tags: Iterable[str], turn: int) -> AgentResponse:
        seed_material = f"{self.name}|{prompt}|{turn}|{','.join(sorted(memory_tags))}"
        rng = random.Random(hashlib.sha256(seed_material.encode()).hexdigest())
        verb = rng.choice(self.verbs)
        twist = rng.choice(_fresh_twists(tuple(memory_tags)))
        proposal = (
            f"{self.name}({self.role})은/는 {self.temperament} 태도로 '{prompt}'에 반응한다. "
            f"{verb} 하려는 순간 {twist}"
        )
        tags = (self.role, verb, twist.split()[0])
        return AgentResponse(
            agent=self.name,
            role=self.role,
            proposal=proposal,
            effect={self.stat_bias: rng.choice([0, 1, 1, 2]), "luck": rng.choice([-1, 0, 1, 2])},
            tags=tags,
        )


def default_agents() -> list[WorldAgent]:
    """Create a compact cast covering places, objects, people, animals, senses, and actions."""

    return [
        WorldAgent("삐딱한 여관", "place", "손님보다 바닥판을 더 믿는", ("길을 제안", "비밀문을 삐걱", "소문을 흘림"), "intelligence"),
        WorldAgent("녹슨 랜턴", "object", "자기 빛을 과장하는", ("그림자를 확대", "암호를 비춤", "불꽃으로 항의"), "dexterity"),
        WorldAgent("계획 집사 프로", "person", "계획표 없이는 숨도 안 쉬는", ("단계를 정리", "위험을 분류", "목표를 고정"), "intelligence"),
        WorldAgent("주머니 늑대", "animal", "작지만 자존심은 보스급인", ("냄새를 추적", "협박성 하품", "꼬리로 지도 작성"), "strength"),
        WorldAgent("다섯 번째 후각", "sense", "없는 냄새까지 맡는", ("단서를 감지", "기분을 색으로 번역", "거짓말 냄새를 지적"), "luck"),
        WorldAgent("성급한 발걸음", "action", "먼저 뛰고 나중에 변명하는", ("돌진", "회피로 착각", "문제를 밟고 지나감"), "stamina"),
    ]


def _fresh_twists(memory_tags: tuple[str, ...]) -> list[str]:
    twists = [
        "세금 걷는 유령이 영수증을 요구한다.",
        "지도 가장자리가 접히며 새로운 골목을 만든다.",
        "고블린 합창단이 전투 BGM을 흥정한다.",
        "냄비가 왕위를 주장하며 결투장을 연다.",
        "어제의 발자국이 오늘의 길안내를 거부한다.",
        "문손잡이가 퀘스트 보상 일부를 선불로 달라고 한다.",
        "하늘의 UI 창이 잠깐 버그처럼 웃는다.",
    ]
    unused = [twist for twist in twists if twist.split()[0] not in memory_tags]
    return unused or twists
