import random
import time
from dataclasses import dataclass
from enum import Enum


class Direction(Enum):
    
    LEFT = "esquerda"
    RIGHT = "direita"


@dataclass(frozen=True)
class ChallengeConfig:
    # quanto a cabeça precisa girar
    target_yaw_degrees: float = 20.0
    # entre um passo e outro
    neutral_yaw_degrees: float = 10.0
    # tempo máximo de cada passo
    step_timeout_seconds: float = 6.0
    
    right_turn_yaw_sign: int = -1


class ChallengeState(Enum):
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"


def draw_challenge(steps: int = 2, random_generator: random.Random | None = None) -> tuple:
    
    random_generator = random_generator or random.SystemRandom()
    sequence = [random_generator.choice(list(Direction))]
    while len(sequence) < steps:
        other_directions = [direction for direction in Direction if direction != sequence[-1]]
        sequence.append(random_generator.choice(other_directions))
    return tuple(sequence)


class HeadTurnChallenge:

    def __init__(self, steps, config: ChallengeConfig = ChallengeConfig(), clock=time.monotonic):
        if not steps:
            raise ValueError("O desafio precisa de pelo menos um passo.")
        self.steps = tuple(steps)
        self.config = config
        self._clock = clock
        self.current_step = 0
        self.state = ChallengeState.IN_PROGRESS
        self._step_started_at = clock()
        self._waiting_return_to_center = False

    @property
    def instruction(self) -> str:
        
        if self.state is ChallengeState.PASSED:
            return "Prova de vida concluída."
        if self.state is ChallengeState.FAILED:
            return "Tempo esgotado. Vamos tentar de novo."
        if self._waiting_return_to_center:
            return "Volte a olhar de frente."
        return f"Vire a cabeça para a {self.steps[self.current_step].value}."

    def update(self, yaw: float | None) -> ChallengeState:
        
        if self.state is not ChallengeState.IN_PROGRESS:
            return self.state

        if self._clock() - self._step_started_at > self.config.step_timeout_seconds:
            self.state = ChallengeState.FAILED
            return self.state

        if yaw is None:
            return self.state

        if self._waiting_return_to_center:
            if abs(yaw) <= self.config.neutral_yaw_degrees:
                self._waiting_return_to_center = False
                self._step_started_at = self._clock()
            return self.state

        yaw_towards_right = yaw * self.config.right_turn_yaw_sign
        expected_direction = self.steps[self.current_step]
        if expected_direction is Direction.RIGHT:
            turned_enough = yaw_towards_right >= self.config.target_yaw_degrees
        else:
            turned_enough = yaw_towards_right <= -self.config.target_yaw_degrees

        if turned_enough:
            self.current_step += 1
            if self.current_step == len(self.steps):
                self.state = ChallengeState.PASSED
            else:
                self._waiting_return_to_center = True
        return self.state