import random

import pytest

from biometrics.challenge import (
    ChallengeConfig,
    ChallengeState,
    Direction,
    HeadTurnChallenge,
    draw_challenge,
)

TURNED_RIGHT, TURNED_LEFT, LOOKING_FORWARD = -30.0, 30.0, 0.0


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_draw_has_the_requested_size_and_never_repeats_in_a_row():
    for seed in range(50):
        sequence = draw_challenge(steps=4, random_generator=random.Random(seed))

        assert len(sequence) == 4
        assert all(first != second for first, second in zip(sequence, sequence[1:]))


def test_draw_varies_between_runs():
    sequences = {draw_challenge(steps=2, random_generator=random.Random(seed)) for seed in range(30)}

    assert len(sequences) > 1


def test_following_the_sequence_passes():
    challenge = HeadTurnChallenge((Direction.RIGHT, Direction.LEFT), clock=FakeClock())

    assert challenge.instruction == "Vire a cabeça para a direita."
    challenge.update(TURNED_RIGHT)
    assert challenge.instruction == "Volte a olhar de frente."
    challenge.update(LOOKING_FORWARD)
    assert challenge.instruction == "Vire a cabeça para a esquerda."
    challenge.update(TURNED_LEFT)

    assert challenge.state is ChallengeState.PASSED
    assert challenge.instruction == "Prova de vida concluída."


def test_turning_to_the_wrong_side_does_not_count():
    challenge = HeadTurnChallenge((Direction.RIGHT,), clock=FakeClock())

    challenge.update(TURNED_LEFT)

    assert challenge.state is ChallengeState.IN_PROGRESS
    assert challenge.current_step == 0


def test_must_return_to_center_between_steps():
    challenge = HeadTurnChallenge((Direction.RIGHT, Direction.LEFT), clock=FakeClock())

    challenge.update(TURNED_RIGHT)
    
    challenge.update(TURNED_LEFT)

    assert challenge.state is ChallengeState.IN_PROGRESS
    assert challenge.instruction == "Volte a olhar de frente."


def test_small_turn_is_not_enough():
    challenge = HeadTurnChallenge((Direction.RIGHT,), clock=FakeClock())

    challenge.update(-10.0)

    assert challenge.state is ChallengeState.IN_PROGRESS


def test_running_out_of_time_fails():
    clock = FakeClock()
    challenge = HeadTurnChallenge((Direction.RIGHT,), clock=clock)

    clock.now = 7.0
    challenge.update(LOOKING_FORWARD)

    assert challenge.state is ChallengeState.FAILED


def test_no_face_does_not_advance_but_time_keeps_running():
    clock = FakeClock()
    challenge = HeadTurnChallenge((Direction.RIGHT,), clock=clock)

    challenge.update(None)
    assert challenge.state is ChallengeState.IN_PROGRESS

    clock.now = 7.0
    challenge.update(None)
    assert challenge.state is ChallengeState.FAILED


def test_each_step_gets_its_own_time():
    clock = FakeClock()
    challenge = HeadTurnChallenge((Direction.RIGHT, Direction.LEFT), clock=clock)

    clock.now = 5.0
    challenge.update(TURNED_RIGHT)
    challenge.update(LOOKING_FORWARD)
    clock.now = 10.0
    challenge.update(TURNED_LEFT)

    assert challenge.state is ChallengeState.PASSED


def test_camera_with_opposite_sign_is_handled_by_the_config():
    
    challenge = HeadTurnChallenge((Direction.RIGHT,), ChallengeConfig(right_turn_yaw_sign=1), clock=FakeClock())

    challenge.update(+30.0)

    assert challenge.state is ChallengeState.PASSED


def test_finished_challenge_does_not_change_anymore():
    challenge = HeadTurnChallenge((Direction.RIGHT,), clock=FakeClock())
    challenge.update(TURNED_RIGHT)

    challenge.update(TURNED_LEFT)

    assert challenge.state is ChallengeState.PASSED


def test_empty_challenge_is_rejected():
    with pytest.raises(ValueError):
        HeadTurnChallenge(())