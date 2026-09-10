
from .values.verdict import Verdict


class Engine():
    APPROVE_LIMIT = 0.75
    REVIEW_LIMIT = 0.55

    def __init__(self, validators_list):
        self.validators_list = validators_list

    def calculate(self, parameter_list):

        validator_result_list = [ validator.validate(parameter_list) for validator in self.validators_list]

        blocked_valitadors = [validator for validator in validator_result_list if validator.block and not validator.passed]

        if blocked_valitadors:
            blocked_reasons = "; ".join([blocked.reason for blocked in blocked_valitadors])
            return Verdict.REJECTED, validator_result_list, blocked_reasons
        else:
            weight_sum = sum(validator.weight for validator in validator_result_list)
            final_score = sum(validator.score * validator.weight for validator in validator_result_list) / weight_sum

            if final_score >= self.APPROVE_LIMIT:
                return Verdict.APPROVED, validator_result_list, ""
            elif final_score >= self.REVIEW_LIMIT:
                return Verdict.PENDING, validator_result_list, "Score final abaixo da faixa de aprovação, requer revisão manual"
            else:
                return Verdict.REJECTED, validator_result_list, "Score final abaixo do mínimo permitido"