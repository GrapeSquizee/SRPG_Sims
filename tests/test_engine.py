from srpg_sims import GameEngine


def test_status_is_hidden_during_normal_turn():
    engine = GameEngine()
    output = engine.handle("여관 문을 연다")

    assert "[Status]" not in output
    assert "Multi-Agent Debate" in output
    assert "status" in output


def test_status_command_reveals_stats_and_plan():
    engine = GameEngine()
    engine.handle("랜턴과 대화한다")
    output = engine.handle("status")

    assert "[Status]" in output
    assert "strength" in output
    assert "Equipment" in output
    assert "[ProAgent Action Plan]" in output


def test_plan_command_only_shows_plan():
    engine = GameEngine()
    output = engine.handle("plan")

    assert output.startswith("[ProAgent Action Plan]")
    assert "Equipment" not in output
