"""Core game engine for a text-first RPG AI-sims experience."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .agents import AgentResponse, WorldAgent, default_agents


@dataclass
class PlayerState:
    """SRPG-like state that is displayed only on request."""

    stats: dict[str, int] = field(default_factory=lambda: {
        "strength": 5,
        "dexterity": 5,
        "intelligence": 5,
        "stamina": 10,
        "luck": 5,
    })
    equipment: list[str] = field(default_factory=lambda: ["낡은 여행복", "연필검"])
    tools: list[str] = field(default_factory=lambda: ["상태창 호출어", "작은 지도 조각"])
    flags: list[str] = field(default_factory=list)


@dataclass
class GameEngine:
    """Runs MAD-like turns and keeps a ProAgent action plan."""

    agents: list[WorldAgent] = field(default_factory=default_agents)
    state: PlayerState = field(default_factory=PlayerState)
    turn: int = 0
    memories: list[str] = field(default_factory=list)
    memory_tags: set[str] = field(default_factory=set)
    current_plan: list[str] = field(default_factory=lambda: [
        "주변 에이전트의 의도를 파악한다.",
        "가장 말이 되는 목표를 하나 고른다.",
        "엉뚱한 변수는 기회로 바꾼다.",
    ])

    def handle(self, prompt: str) -> str:
        """Process player text while keeping status hidden unless requested."""

        normalized = prompt.strip().lower()
        if normalized in {"status", "상태", "상태창"}:
            return self.render_status()
        if normalized in {"plan", "계획", "action plan"}:
            return self.render_plan()
        if normalized in {"look", "보기", "둘러보기"}:
            prompt = "주변을 자세히 둘러본다"
        if normalized in {"quit", "exit", "종료"}:
            return "세계가 책갈피처럼 접힙니다. 다시 열면 이어서 이상해질 준비가 되어 있습니다."
        return self._advance(prompt.strip() or "조심스럽게 한 걸음 내딛는다")

    def _advance(self, prompt: str) -> str:
        self.turn += 1
        debaters = self._select_agents(prompt)
        responses = [agent.respond(prompt, self.memory_tags, self.turn) for agent in debaters]
        chosen = self._choose_response(responses)
        self._apply(chosen)
        self._refresh_plan(prompt, chosen)
        self.memories.append(chosen.proposal)
        self.memory_tags.update(chosen.tags)
        debate = "\n".join(f"- {response.proposal}" for response in responses)
        return (
            f"[Turn {self.turn}] Multi-Agent Debate\n{debate}\n\n"
            f"Director: {chosen.agent}의 의견을 채택합니다. {chosen.proposal}\n"
            "(상태창은 숨겨져 있습니다. 보고 싶으면 `status`, 계획만 보려면 `plan`을 입력하세요.)"
        )

    def _select_agents(self, prompt: str) -> list[WorldAgent]:
        lowered = prompt.lower()
        selected = [agent for agent in self.agents if agent.role in lowered or agent.name in prompt]
        if len(selected) < 3:
            selected.extend(agent for agent in self.agents if agent not in selected)
        return selected[:4]

    def _choose_response(self, responses: list[AgentResponse]) -> AgentResponse:
        def score(response: AgentResponse) -> float:
            novelty_penalty = max((SequenceMatcher(None, response.proposal, old).ratio() for old in self.memories), default=0)
            plan_bonus = 0.2 if response.role in {"person", "action", "place"} else 0
            return sum(response.effect.values()) + plan_bonus - novelty_penalty * 3

        return max(responses, key=score)

    def _apply(self, response: AgentResponse) -> None:
        for stat, delta in response.effect.items():
            self.state.stats[stat] = max(0, self.state.stats[stat] + delta)
        flag = f"Turn {self.turn}: {response.agent}와 사건 발생"
        self.state.flags.append(flag)
        if response.role == "object" and response.agent not in self.state.tools:
            self.state.tools.append(response.agent)

    def _refresh_plan(self, prompt: str, response: AgentResponse) -> None:
        self.current_plan = [
            f"'{prompt}' 목표를 {response.agent}의 단서로 재해석한다.",
            "충돌한 에이전트들의 주장을 한 번 더 검증한다.",
            "반복되는 사건은 피하고 새 장소/감각/행동을 섞는다.",
            "위험하면 장비나 편리한 도구를 사용한다.",
        ]

    def render_status(self) -> str:
        stats = "\n".join(f"  - {key}: {value}" for key, value in self.state.stats.items())
        equipment = ", ".join(self.state.equipment) or "없음"
        tools = ", ".join(self.state.tools) or "없음"
        flags = "\n".join(f"  - {flag}" for flag in self.state.flags[-5:]) or "  - 아직 없음"
        return f"[Status]\nStats:\n{stats}\nEquipment: {equipment}\nTools: {tools}\nRecent Flags:\n{flags}\n\n{self.render_plan()}"

    def render_plan(self) -> str:
        plan = "\n".join(f"  {index}. {step}" for index, step in enumerate(self.current_plan, start=1))
        return f"[ProAgent Action Plan]\n{plan}"
