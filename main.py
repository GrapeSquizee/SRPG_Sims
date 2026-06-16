from __future__ import annotations

import argparse
import json
import os
import random
import sys
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple


STATS = ("STR", "AGI", "INT", "VIT", "LUK")


def configure_console() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def compact(text: str, limit: int = 700) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


@dataclass
class Player:
    name: str
    title: str = "길 잃은 전술가"
    hp: int = 24
    max_hp: int = 24
    stats: Dict[str, int] = field(
        default_factory=lambda: {"STR": 5, "AGI": 5, "INT": 6, "VIT": 5, "LUK": 7}
    )
    equipment: List[str] = field(default_factory=lambda: ["닳은 여행 망토", "말을 잘 듣는 빈 주머니"])
    tools: List[str] = field(default_factory=lambda: ["상태창", "의심스러운 나침반"])
    memory: List[str] = field(default_factory=list)

    def remember(self, text: str) -> None:
        self.memory = (self.memory + [compact(text, 240)])[-8:]

    def change_stat(self, stat: str, delta: int) -> None:
        self.stats[stat] = max(1, self.stats[stat] + delta)

    def add_unique(self, target: List[str], item: str) -> None:
        item = compact(item, 40)
        if item and item not in target:
            target.append(item)


@dataclass(frozen=True)
class Agent:
    name: str
    kind: str
    voice: str
    bias: str
    wants: Tuple[str, ...]

    def speak(self, prompt: str, player: Player) -> str:
        verbs = {
            "person": ["따져 묻는다", "속삭인다", "거래를 제안한다"],
            "place": ["울림으로 답한다", "문턱을 바꾼다", "먼지를 흔든다"],
            "object": ["삐걱이며 주장한다", "빛을 낸다", "쓸모를 과장한다"],
            "animal": ["냄새를 맡고 판단한다", "눈치를 본다", "길을 가로막는다"],
            "sense": ["감각을 증폭한다", "불길한 세부를 건넨다", "기억을 건드린다"],
            "action": ["절차를 요구한다", "순서를 재배열한다", "계획표를 펼친다"],
        }
        hook = ""
        if player.memory and random.random() < 0.35:
            hook = f" 지난 기억 '{random.choice(player.memory)}'도 근거로 삼는다."
        return (
            f"{self.name}: {self.voice} 말투로 {random.choice(verbs[self.kind])}. "
            f"'{prompt}'라면 {random.choice(self.wants)} 쪽이 낫다고 우긴다.{hook}"
        )


@dataclass
class ActionPlan:
    goal: str = "첫 번째 안전지대를 확보하고 세계의 규칙을 알아낸다"
    steps: List[str] = field(
        default_factory=lambda: [
            "주변 에이전트의 의도를 파악한다",
            "쓸 수 있는 도구나 동맹을 얻는다",
            "작은 사건을 해결해 안전지대를 만든다",
            "다음 지역으로 이어지는 단서를 찾는다",
        ]
    )
    current_step: int = 0

    @property
    def current(self) -> str:
        return self.steps[min(self.current_step, len(self.steps) - 1)]

    def advance(self) -> None:
        self.current_step = min(self.current_step + 1, len(self.steps) - 1)

    def render(self) -> str:
        lines = [f"목표: {self.goal}"]
        for idx, step in enumerate(self.steps):
            marker = ">" if idx == self.current_step else " "
            done = "x" if idx < self.current_step else " "
            lines.append(f" {marker} [{done}] {idx + 1}. {step}")
        return "\n".join(lines)


@dataclass
class World:
    turn: int = 0
    location: str = "유리 종탑 아래 시장"
    mood: str = "기묘하게 평화로움"
    danger: int = 1
    novelty_log: List[str] = field(default_factory=list)
    plan: ActionPlan = field(default_factory=ActionPlan)

    def remember_novelty(self, key: str) -> None:
        self.novelty_log = (self.novelty_log + [key])[-20:]


class ContentModel(Protocol):
    label: str

    def debate(self, prompt: str, agents: Sequence[Agent], world: World, player: Player) -> Optional[Dict[str, Any]]:
        ...

    def event(
        self, prompt: str, decision: str, stat: str, success: bool, world: World, player: Player
    ) -> Optional[Dict[str, Any]]:
        ...


class LocalModel:
    label = "local-rules"

    def debate(self, prompt: str, agents: Sequence[Agent], world: World, player: Player) -> Optional[Dict[str, Any]]:
        return None

    def event(
        self, prompt: str, decision: str, stat: str, success: bool, world: World, player: Player
    ) -> Optional[Dict[str, Any]]:
        return None


class OllamaModel:
    def __init__(self, model: str, base_url: str, timeout: int) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.label = f"ollama:{model}"
        self.last_error: Optional[str] = None

    def debate(self, prompt: str, agents: Sequence[Agent], world: World, player: Player) -> Optional[Dict[str, Any]]:
        agent_text = "\n".join(
            f"- {a.name}: kind={a.kind}, voice={a.voice}, bias={a.bias}, wants={', '.join(a.wants)}"
            for a in agents
        )
        return self._generate(
            "너는 텍스트 기반 SRPG AI Sims의 콘텐츠 디렉터다. 모든 사물, 장소, 감각, 행동이 에이전트처럼 발언한다. "
            "말은 되지만 엉뚱하고 재미있게 만들고, 이전 기억을 반복하지 않는다. 반드시 한국어 JSON만 출력한다.",
            f"""
위치: {world.location}
분위기: {world.mood}
위험도: {world.danger}
현재 계획 단계: {world.plan.current}
플레이어 스탯: {player.stats}
최근 기억: {player.memory[-5:]}
최근 novelty key: {world.novelty_log[-8:]}
유저 입력: {prompt}
참여 에이전트:
{agent_text}

JSON 형식:
{{"statements":["에이전트명: 짧은 주장"],"decision":"토론 결론 한 문단","mood":"선택 사항","location":"선택 사항"}}
""",
        )

    def event(
        self, prompt: str, decision: str, stat: str, success: bool, world: World, player: Player
    ) -> Optional[Dict[str, Any]]:
        return self._generate(
            "너는 SRPG 로그 작가다. 판정 결과를 두 문장 이하의 게임 이벤트로 만든다. 보상 수치는 바꾸지 않는다. 한국어 JSON만 출력한다.",
            f"""
유저 입력: {prompt}
토론 결론: {decision}
판정 스탯: {stat}
성공 여부: {success}
위치: {world.location}
분위기: {world.mood}
위험도: {world.danger}
최근 기억: {player.memory[-5:]}

JSON 형식:
{{"event":"사건 결과","reward_tool":"선택 사항 또는 빈 문자열","reward_equipment":"선택 사항 또는 빈 문자열","mood":"선택 사항"}}
""",
        )

    def _generate(self, system: str, user: str) -> Optional[Dict[str, Any]]:
        payload = {
            "model": self.model,
            "prompt": f"{system}\n\n{user}",
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.95, "top_p": 0.9, "num_predict": 700},
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
            result = json.loads(raw.get("response", ""))
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            self.last_error = str(exc)
            return None
        self.last_error = None
        return result if isinstance(result, dict) else None


class OpenAICompatibleModel:
    def __init__(self, model: str, base_url: str, api_key: str, timeout: int) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.label = f"openai-compatible:{model}"
        self.last_error: Optional[str] = None

    def debate(self, prompt: str, agents: Sequence[Agent], world: World, player: Player) -> Optional[Dict[str, Any]]:
        agent_text = "\n".join(
            f"- {a.name}: kind={a.kind}, voice={a.voice}, bias={a.bias}, wants={', '.join(a.wants)}"
            for a in agents
        )
        return self._chat_json(
            "너는 텍스트 기반 SRPG AI Sims의 콘텐츠 디렉터다. 모든 사물, 장소, 감각, 행동이 에이전트처럼 발언한다. "
            "말은 되지만 엉뚱하고 재미있게 만들고, 이전 기억을 반복하지 않는다. 반드시 한국어 JSON 객체만 출력한다.",
            f"""
위치: {world.location}
분위기: {world.mood}
위험도: {world.danger}
현재 계획 단계: {world.plan.current}
플레이어 스탯: {player.stats}
최근 기억: {player.memory[-5:]}
최근 novelty key: {world.novelty_log[-8:]}
유저 입력: {prompt}
참여 에이전트:
{agent_text}

JSON 형식:
{{"statements":["에이전트명: 짧은 주장"],"decision":"토론 결론 한 문단","mood":"선택 사항","location":"선택 사항"}}
""",
        )

    def event(
        self, prompt: str, decision: str, stat: str, success: bool, world: World, player: Player
    ) -> Optional[Dict[str, Any]]:
        return self._chat_json(
            "너는 SRPG 로그 작가다. 판정 결과를 두 문장 이하의 게임 이벤트로 만든다. 보상 수치는 바꾸지 않는다. 한국어 JSON 객체만 출력한다.",
            f"""
유저 입력: {prompt}
토론 결론: {decision}
판정 스탯: {stat}
성공 여부: {success}
위치: {world.location}
분위기: {world.mood}
위험도: {world.danger}
최근 기억: {player.memory[-5:]}

JSON 형식:
{{"event":"사건 결과","reward_tool":"선택 사항 또는 빈 문자열","reward_equipment":"선택 사항 또는 빈 문자열","mood":"선택 사항"}}
""",
        )

    def _chat_json(self, system: str, user: str) -> Optional[Dict[str, Any]]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.95,
            "top_p": 0.9,
            "max_tokens": 700,
            "response_format": {"type": "json_object"},
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
            content = raw["choices"][0]["message"]["content"]
            result = json.loads(content)
        except (KeyError, IndexError, OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            self.last_error = str(exc)
            return None
        self.last_error = None
        return result if isinstance(result, dict) else None


def default_agents() -> List[Agent]:
    return [
        Agent("빚쟁이 촛대", "object", "건조하지만 과장된", "risk", ("대가를 먼저 계산하는", "빛을 담보로 협상하는")),
        Agent("계단 냄새", "sense", "묘하게 시적인", "memory", ("숨겨진 길을 맡아보는", "잊은 약속을 떠올리는")),
        Agent("종탑 광장", "place", "느리고 장엄한", "order", ("모두를 제 위치에 세우는", "규칙을 먼저 확인하는")),
        Agent("반쯤 투명한 경비병", "person", "공손하지만 허술한", "law", ("통행증을 요구하는", "허점을 법으로 포장하는")),
        Agent("주머니 속 개구리 동전", "animal", "짧고 뻔뻔한", "luck", ("운에 맡기는", "작은 도박을 거는")),
        Agent("후퇴라는 행동", "action", "차갑고 실무적인", "plan", ("피해를 줄이는", "다음 수를 남기는")),
        Agent("정면돌파라는 행동", "action", "뜨겁고 단순한", "force", ("일단 밀어붙이는", "기세로 판을 바꾸는")),
    ]


class Game:
    def __init__(self, model: ContentModel) -> None:
        self.model = model
        self.agents = default_agents()

    def select_agents(self, world: World) -> List[Agent]:
        random.shuffle(self.agents)
        selected = self.agents[:4]
        if world.turn % 3 == 0:
            extra = [agent for agent in self.agents if agent.kind == "action" and agent not in selected]
            if extra:
                selected.append(random.choice(extra))
        return selected

    def debate(self, prompt: str, agents: Sequence[Agent], world: World, player: Player) -> Tuple[str, List[str]]:
        generated = self.model.debate(prompt, agents, world, player)
        if generated:
            statements = [compact(item, 260) for item in generated.get("statements", []) if str(item).strip()]
            decision = compact(generated.get("decision", ""), 500)
            if len(statements) >= 2 and decision:
                world.mood = compact(generated.get("mood") or world.mood, 60)
                world.location = compact(generated.get("location") or world.location, 60)
                return decision, statements

        statements = [agent.speak(prompt, player) for agent in agents]
        proposal = self.choose_local_proposal(agents, world, player)
        twist = random.choice(
            [
                "단, 누군가가 말하면 안 되는 이름을 영수증에 적는다.",
                "대신 주변 사물들이 잠시 직업 윤리를 갖게 된다.",
                "그러나 결과가 너무 그럴듯해서 오히려 수상해진다.",
                "그리고 아무도 요청하지 않은 작은 의식이 시작된다.",
            ]
        )
        return f"토론 결론: {proposal}. {twist} 현재 계획 단계는 '{world.plan.current}'이다.", statements

    def choose_local_proposal(self, agents: Sequence[Agent], world: World, player: Player) -> str:
        proposals = {
            "plan": "계획을 유지하되 손실을 줄이는 우회",
            "force": "위험을 감수하고 장면의 주도권을 잡기",
            "luck": "작은 우연을 이용해 예상 밖의 보상 얻기",
            "memory": "이전 단서와 연결된 숨은 통로 찾기",
            "law": "규칙의 빈틈을 이용한 합법적 억지",
            "risk": "대가를 지불하고 즉시 쓸 수 있는 이득 획득",
            "order": "질서를 세워 안전한 선택지 확보",
        }
        scored = []
        for agent in agents:
            proposal = proposals[agent.bias]
            score = random.randint(1, 8)
            score += 2 if agent.bias == "plan" else 0
            score += player.stats["LUK"] // 3 if agent.bias == "luck" else 0
            score += player.stats["STR"] // 3 if agent.bias == "force" else 0
            score += 2 if world.danger > 3 and agent.bias == "plan" else 0
            scored.append((score, proposal))
        return max(scored)[1]

    def resolve(self, prompt: str, decision: str, world: World, player: Player) -> str:
        stat = random.choice(STATS)
        success = player.stats[stat] + random.randint(1, 10) >= 7 + world.danger
        key = f"{'-'.join(prompt.lower().split()[:4])}:{'-'.join(decision.lower().split()[:4])}"

        if key in world.novelty_log:
            event = "익숙한 사건이 반복되려는 순간, 세계가 스스로 민망해하며 장면을 비튼다. LUK+1."
            player.change_stat("LUK", 1)
        elif success:
            event = f"{stat} 판정 성공. 결론이 이상하게 잘 먹혔다. {stat}+1."
            player.change_stat(stat, 1)
            if random.random() < 0.55:
                world.plan.advance()
        else:
            loss = random.randint(1, 4)
            player.hp = max(1, player.hp - loss)
            world.danger = min(5, world.danger + 1)
            event = f"{stat} 판정 실패. 결론은 통했지만 비용이 붙었다. HP-{loss}, 위험도+1."

        generated = self.model.event(prompt, decision, stat, success, world, player)
        if generated and isinstance(generated.get("event"), str):
            event = compact(generated["event"], 360)
            player.add_unique(player.tools, generated.get("reward_tool", ""))
            player.add_unique(player.equipment, generated.get("reward_equipment", ""))
            world.mood = compact(generated.get("mood") or world.mood, 60)
        else:
            for token, reward in [("우연", "접히는 행운표"), ("숨은", "먼지 묻은 열쇠문장"), ("합법", "임시 통행 논리"), ("계획", "작전용 분필")]:
                if token in decision and random.random() < 0.5:
                    player.add_unique(player.tools, reward)

        world.remember_novelty(key)
        world.turn += 1
        player.remember(f"{world.location}: {decision}")
        if random.random() < 0.25:
            world.mood = random.choice(["소란스러움", "기묘하게 평화로움", "비가 올 듯한 긴장", "회의적인 축제 분위기"])
        if world.turn % 4 == 0:
            world.danger = max(1, world.danger - 1)
        return event


def box(title: str, body: str) -> None:
    width = 78
    print("\n" + "=" * width)
    print(f" {title}")
    print("-" * width)
    for line in body.splitlines():
        print(textwrap.fill(line, width=width, replace_whitespace=False))
    print("=" * width)


def render_status(player: Player, world: World, model_label: str) -> str:
    stats = "  ".join(f"{key}:{player.stats[key]}" for key in STATS)
    memory = "\n".join(f"- {item}" for item in player.memory[-5:]) or "- 아직 없음"
    return (
        f"{player.name} / {player.title}\n"
        f"HP {player.hp}/{player.max_hp} | 위치: {world.location} | 분위기: {world.mood} | 위험도: {world.danger}\n"
        f"콘텐츠 모델: {model_label}\n"
        f"{stats}\n\n"
        f"장비: {', '.join(player.equipment) or '없음'}\n"
        f"도구: {', '.join(player.tools) or '없음'}\n\n"
        f"[Action Plan]\n{world.plan.render()}\n\n"
        f"[기억]\n{memory}"
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SRPG 스타일 텍스트 AI Sims")
    parser.add_argument("--ai", action="store_true", help="하위 호환 옵션. 지정하면 Ollama provider를 사용한다.")
    parser.add_argument(
        "--provider",
        choices=["local", "ollama", "openai-compatible"],
        default=None,
        help="콘텐츠 모델 provider",
    )
    parser.add_argument("--model", default="qwen2.5:3b", help="모델 이름")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama 서버 URL")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        help="OpenAI-compatible API base URL. 예: https://api.openai.com/v1",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY", ""),
        help="OpenAI-compatible API key. 미지정 시 OPENAI_API_KEY 환경변수를 사용한다.",
    )
    parser.add_argument("--timeout", type=int, default=45, help="모델 요청 타임아웃 초")
    return parser.parse_args(argv)


def build_model(args: argparse.Namespace) -> ContentModel:
    provider = args.provider or ("ollama" if args.ai else "local")
    if provider == "ollama":
        return OllamaModel(args.model, args.ollama_url, args.timeout)
    if provider == "openai-compatible":
        return OpenAICompatibleModel(args.model, args.base_url, args.api_key, args.timeout)
    return LocalModel()


def run(argv: Optional[Sequence[str]] = None) -> None:
    configure_console()
    args = parse_args(argv)
    model = build_model(args)
    game = Game(model)
    world = World()

    box("SRPG AI Sims", "텍스트 기반 다중 에이전트 SRPG 프로토타입입니다. 사물, 장소, 감각, 행동이 토론해서 사건을 만듭니다.")
    player = Player(input("이름을 입력하세요: ").strip() or "이름 없는 유저")
    box("시작", render_status(player, world, model.label))
    box("명령어", "아무 문장: 행동/대화/관찰\n/status: 상태창\n/plan: Action Plan\n/ai: 모델 정보\n/help: 도움말\n/quit: 종료")

    while True:
        prompt = input("\n> ").strip()
        if not prompt:
            continue
        if prompt == "/quit":
            print("세계가 당신을 북마크에 끼워 둡니다.")
            return
        if prompt == "/status":
            box("Status", render_status(player, world, model.label))
            continue
        if prompt == "/plan":
            box("Action Plan", world.plan.render())
            continue
        if prompt == "/ai":
            detail = f"모델: {model.label}"
            if getattr(model, "last_error", None):
                detail += f"\n최근 폴백 이유: {getattr(model, 'last_error')}"
            box("AI", detail)
            continue
        if prompt == "/help":
            box("명령어", "아무 문장: 행동/대화/관찰\n/status: 상태창\n/plan: Action Plan\n/ai: 모델 정보\n/help: 도움말\n/quit: 종료")
            continue

        agents = game.select_agents(world)
        decision, statements = game.debate(prompt, agents, world, player)
        event = game.resolve(prompt, decision, world, player)
        box("Agent Debate", "\n".join(f"- {line}" for line in statements))
        box("Scene Result", f"{decision}\n\n{event}")
        box("Status", render_status(player, world, model.label))


if __name__ == "__main__":
    run()
