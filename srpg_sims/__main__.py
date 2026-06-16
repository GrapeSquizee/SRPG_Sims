"""Command-line interface for SRPG Sims."""

from .engine import GameEngine


def main() -> None:
    engine = GameEngine()
    print("SRPG Sims에 접속했습니다. 무엇을 하시겠습니까? (`status`, `plan`, `quit` 사용 가능)")
    while True:
        try:
            prompt = input("> ")
        except EOFError:
            print()
            break
        output = engine.handle(prompt)
        print(output)
        if prompt.strip().lower() in {"quit", "exit", "종료"}:
            break


if __name__ == "__main__":
    main()
